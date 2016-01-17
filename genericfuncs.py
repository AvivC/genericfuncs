from __future__ import unicode_literals, division, print_function, absolute_import

import collections
import inspect
from collections import namedtuple
import functools


class generic(object):
    """
    A decorator to turn functions into generic functions.
    Upon invocation of a generic function, the registered predicates are invoked
    in order of registration, passing in the arguments to the function.
    The first predicate returning True, has its mapped implementation invoked.

    A predicate may be any one of the following:
    Types, any boolean callable, or lists of predicates (with AND relations):

        @genericfuncs.generic
        def func(a):
            # default implementation
            raise TypeError()

        @func.when(int)  # dispatch on type
        def _when_int(a):
            return a * a

        @func.when(lambda a: a == 'magic')  # dispatch on arbitrary predicates
        def _when_magic_word(a):
            return a.upper()

        @func.when([float, lambda a: a < 0])  # dispatch on multiple predicates
        def _when_float_and_negative(a):
            return a * -1

        func(10) --> 100  # _when_int invoked
        func('magic') --> 'MAGIC'  # _when_magic_word invoked
        func(-5.5) --> 5.5  # _when_float_and_negative
        func(Something()) --> TypeError raised  # default implementation invoked

    Arguments are injected into predicates by their name. This allows predicates to list which of the
    arguments they want to consider.

    The same goes for implementations - the parameters are injected by name, and not all arguments must be listed.

        @generic
        def multiple_params_func(a, b, c):
            return a + b + c  # default implementation

        @multiple_params_func.when(lambda b: b > 10)  # only inject paramter `b` to the predicate
        def _when_b_greater_than_10(a):  # only inject `a`
            return a * 10

        @multiple_params_func.when(lambda a, b: a % b == 0)  # inject only `a` and `b`
        def _when_a_divisible_by_c(a, b, c):
            return a / b * c

    The call site however, must always list all mandatory arguments, as always.

        multiple_params_func(10, 20, 30) --> 100  # _when_b_great_than_10 invoked
        multiple_params_func(4, 2, 'bla') --> 'blabla'  # _when_a_divisible_by_c invoked
        multiple_params_func(0, 0, 0) --> 0  # default implementation invoked

    More info about the when() decorator can be found in its docs.
    """

    def __init__(self, wrapped):
        self._base_func = _FunctionInfo(wrapped)
        self._predicates_and_funcs = []
        functools.update_wrapper(self, wrapped)

    def __call__(self, *args, **kwargs):
        self._validate_args(args, kwargs)

        for predicate, func in self._predicates_and_funcs:
            if self._invoke_partial_func(predicate, args, kwargs):
                return self._invoke_partial_func(func, args, kwargs)

        return self._base_func(*args, **kwargs)

    def _validate_args(self, args, kwargs):
        if any(kwarg not in self._base_func.args for kwarg in kwargs):
            raise ValueError('One or more keyword arguments don\'t exist in the generic function.')
        if len(args) > len(self._base_func.args):
            raise ValueError('Received too many positional arguments.')

    def _invoke_partial_func(self, partial_func, input_args, input_kwargs):
        partial_args, partial_kwargs = \
            self._get_partial_func_arg_and_kwarg_values(partial_func.args, input_args, input_kwargs)
        try:
            return partial_func(*partial_args, **partial_kwargs)
        except partial_func.ignored_errors:
            return False

    def _get_partial_func_arg_and_kwarg_values(self, partial_func_arg_names, input_arg_values, input_kwargs):
        partial_args = self._find_partial_arg_values(input_arg_values, partial_func_arg_names)
        partial_kwargs = {k: v for k, v in input_kwargs.iteritems() if k in partial_func_arg_names}
        return partial_args, partial_kwargs

    def _find_partial_arg_values(self, input_arg_values, partial_func_arg_names):
        unnecessary_arg_names = set(self._base_func.args) - set(partial_func_arg_names)
        unnecessary_arg_indexes = [self._base_func.args.index(arg_name) for arg_name in unnecessary_arg_names]
        return [arg_value for index, arg_value in enumerate(input_arg_values)
                if index not in unnecessary_arg_indexes]

    def when(self, predicate, ignored_errors=None):
        """
        A decorator used to register an implementation to a generic function.
        The decorator takes a predicate, to which the implementation will be mapped.
        Upon invocation of the generic function, the first implementation whose
        predicate returned True will be invoked.

        :param predicate: The predicate may be any one of the following options:
                            A type (meaning an `isinstance()` check), a callable that returns a boolean,
                            or a list of predicates (with AND relations between them):
        :param ignored_errors: A list of exception types that should not be propagated
                               if raised inside the predicate.
                               For example:

                                    @my_generic_func.when(lambda a: a > 10, ignored_errors=[TypeError])
                                    def _implementation(a):
                                        ...

                               When invoking `my_generic_func(MyThing())`, a TypeError will be raised
                               inside the predicate, probably crashing the program.
                               This is because MyThing objects don't support `>` operator.
                               Specifying `ignored_errors=[TypeError]` makes the error be silently ignored,
                               moving on to the next predicate.
        """
        predicate_info = self._make_predicate_info(predicate, ignored_errors=ignored_errors)

        def dec(func):
            impl_info = _FunctionInfo(func)

            if not self._all_params_valid(predicate_info):
                raise ValueError('Argument specified in predicate doesn\'t exist in base function.')
            if not self._all_params_valid(impl_info):
                raise ValueError('Argument specified in implementation doesn\'t exist in base function.')

            self._predicates_and_funcs.append(_PredicateFunctionMappping(predicate_info, impl_info))
            return func

        return dec

    def _make_predicate_info(self, predicate, ignored_errors=None):
        if isinstance(predicate, collections.Callable):
            if inspect.isfunction(predicate) or inspect.ismethod(predicate):
                return _FunctionInfo(predicate, ignored_errors=ignored_errors)
            elif isinstance(predicate, type):
                return self._make_type_predicate(predicate, ignored_errors=ignored_errors)
            else:  # callable object
                return _FunctionInfo(predicate.__call__, ignored_errors=ignored_errors)
        elif isinstance(predicate, collections.Iterable):
            return self._compose_predicates(predicate, ignored_errors=ignored_errors)
        else:
            raise TypeError('Input to when() is not a callable nor an iterable of callables.')

    def _make_type_predicate(self, predicate, ignored_errors=None):
        def type_predicate(*args, **kwargs):
            return all(isinstance(obj, predicate) for obj in args) \
                   and all(isinstance(obj, predicate) for key, obj in kwargs.iteritems())
        return _FunctionInfo(type_predicate, args=self._base_func.args, ignored_errors=ignored_errors)

    def _compose_predicates(self, predicates, ignored_errors=None):
        predicate_infos = map(self._make_predicate_info, predicates)

        def composed_predicates(*args, **kwargs):
            return all(self._invoke_partial_func(predicate, args, kwargs)
                       for predicate in predicate_infos)

        return _FunctionInfo(composed_predicates, args=self._base_func.args, ignored_errors=ignored_errors)

    def _all_params_valid(self, function_info):
        return all(arg in self._base_func.args for arg in function_info.args)


_PredicateFunctionMappping = namedtuple('PredicateFunctionMappping', ['predicate_info', 'func_info'])


class _FunctionInfo(object):
    def __init__(self, function, args=None, ignored_errors=None):
        self.function = function
        self.ignored_errors = () if ignored_errors is None else tuple(ignored_errors)

        if args is None:
            self.args = function.__code__.co_varnames[:function.__code__.co_argcount]
            if inspect.ismethod(function):
                self.args = self.args[1:]  # strip self argument
        else:
            self.args = args

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)
