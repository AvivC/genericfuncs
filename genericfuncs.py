from __future__ import unicode_literals, division, print_function, absolute_import

import collections
import inspect
from collections import namedtuple
import functools
from itertools import imap


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
        # allow passing in ready _FunctionInfo objects
        self._base_func = wrapped if isinstance(wrapped, _FunctionInfo) else _FunctionInfo(wrapped)
        self._predicates_and_funcs = []
        # functools.update_wrapper(self, wrapped)

    def __call__(self, *args, **kwargs):
        self._validate_args(args, kwargs)

        for predicate, function in self._predicates_and_funcs:
            if predicate(*args, **kwargs):
                return function(*args, **kwargs)

        return self._base_func(*args, **kwargs)

    def _validate_args(self, args, kwargs):
        if any(kwarg not in self._base_func.args for kwarg in kwargs):
            raise ValueError('One or more keyword arguments don\'t exist in the generic function.')
        if len(args) > len(self._base_func.args):
            raise ValueError('Received too many positional arguments.')

    def when(self, predicate_source, type=None):
        """
        A decorator used to register an implementation to a generic function.
        The decorator takes a predicate, to which the implementation will be mapped.
        Upon invocation of the generic function, the first implementation whose
        predicate returned True will be invoked.

        :param predicate_source: The predicate may be any one of the following options:
                            A type (meaning an `isinstance()` check), a callable that returns a boolean,
                            or a list of predicates (with AND relations between them):
        """
        predicate = self.make_predicate(predicate_source, prepend_typecheck=type)

        def dec(func):
            impl_info = _PartialFunction(func, self._base_func)

            if not self._all_params_valid(predicate):
                raise ValueError('Argument specified in predicate doesn\'t exist in base function.')
            if not self._all_params_valid(impl_info):
                raise ValueError('Argument specified in implementation doesn\'t exist in base function.')

            self._predicates_and_funcs.append(_PredicateFunctionMappping(predicate, impl_info))
            return func

        return dec

    def make_predicate(self, predicate_source, prepend_typecheck=None):
        if isinstance(predicate_source, collections.Callable):
            predicate = self._make_predicate_from_callable(predicate_source)
        elif isinstance(predicate_source, dict):
            predicate = self._make_predicate_from_dict(predicate_source)
        elif isinstance(predicate_source, collections.Iterable):  # this check must appear after the dict check
            predicate = self._make_predicate_from_iterable(predicate_source)
        else:
            raise TypeError('Input to when() is not a callable, a dict or an iterable of callables.')

        if prepend_typecheck is None:
            return predicate
        else:
            return self._prepend_typecheck_to_predicate(prepend_typecheck, predicate)

    def _make_predicate_from_callable(self, predicate_source):
        if isinstance(predicate_source, _PartialFunction):
            return predicate_source  # allow passing already ready predicates, but return them as is

        elif inspect.isfunction(predicate_source) or inspect.ismethod(predicate_source):
            return _PartialFunction(predicate_source, self._base_func)

        elif isinstance(predicate_source, type):
            return self._make_type_predicate(predicate_source)

        else:  # different callable object
            return _PartialFunction(predicate_source.__call__, self._base_func)

    def _make_predicate_from_dict(self, predicate_dict):
        def predicate(*args, **kwargs):
            for arg_name, arg_predicate_source in predicate_dict.iteritems():
                arg_value = self._base_func.get_arg_value(arg_name, args, kwargs)

                gen = generic(_FunctionInfo(args=[arg_name]))
                arg_predicate = gen.make_predicate(arg_predicate_source)

                if not arg_predicate(arg_value):
                    return False
            return True

        return _PartialFunction(predicate, self._base_func, self._base_func.args)

    def _make_type_predicate(self, predicate):
        if isinstance(predicate, type):
            def type_predicate(*args, **kwargs):
                return all(isinstance(obj, predicate) for obj in args) \
                       and all(isinstance(obj, predicate) for key, obj in kwargs.iteritems())

        elif isinstance(predicate, dict):
            if any((not isinstance(value, (type, collections.Iterable))) for value in predicate.values()):
                raise TypeError('In a dict that maps arguments to expected types, '
                                'the values must be either types or iterables of types.')

            def type_predicate(*args, **kwargs):
                for arg_name, expected_arg_type in predicate.iteritems():
                    arg_value = self._base_func.get_arg_value(arg_name, args, kwargs)

                    if isinstance(expected_arg_type, collections.Iterable):
                        expected_arg_type = tuple(expected_arg_type)

                    if not isinstance(arg_value, expected_arg_type):
                        return False
                return True

        else:
            raise TypeError('A type predicate may be created from a type or a dictionary.')

        return _PartialFunction(type_predicate, self._base_func, args=self._base_func.args)

    def _make_predicate_from_iterable(self, predicates, aggregator=all):
        partial_func_predicates = map(self.make_predicate, predicates)

        def composed_predicates(*args, **kwargs):
            return aggregator(predicate(*args, **kwargs) for predicate in partial_func_predicates)

        return _PartialFunction(composed_predicates, self._base_func, args=self._base_func.args)

    def _prepend_typecheck_to_predicate(self, prepend_typecheck, predicate):
        if isinstance(prepend_typecheck, (type, dict)):
            type_checker = self._make_type_predicate(prepend_typecheck)
        elif isinstance(prepend_typecheck, collections.Iterable):
            type_checker = self._make_predicate_from_iterable(prepend_typecheck, aggregator=any)
        else:
            raise ValueError('type optional argument to when() has to be a type or an iterable of types. '
                             'Can\'t be a {}.'.format(type(prepend_typecheck)))

        return self._make_predicate_from_iterable([type_checker, predicate])

    def _all_params_valid(self, function_info):
        return all(arg in self._base_func.args for arg in function_info.args)


_PredicateFunctionMappping = namedtuple('PredicateFunctionMappping', ['predicate_info', 'func_info'])


class _FunctionInfo(object):
    def __init__(self, function=None, args=None):
        self._function = function if function is not None else lambda *args, **kwargs: None

        if args is None:
            self.args = function.__code__.co_varnames[:function.__code__.co_argcount]
            if inspect.ismethod(function):
                self.args = self.args[1:]  # strip self argument
        else:
            self.args = args

    def __call__(self, *args, **kwargs):
        return self._function(*args, **kwargs)

    def get_arg_value(self, arg_name, input_args, input_kwargs):
        try:
            return input_kwargs[arg_name]
        except KeyError:
            pass
        try:
            arg_index = self.args.index(arg_name)
            return input_args[arg_index]
        except IndexError:
            raise ValueError('Specified argument doesn\'t exist in generic function.')


class _PartialFunction(_FunctionInfo):
    """A _PartialFunction is a function that is only interested
    in some of the arguments to another function (the base function).
    For example, the base function might take parameters a, b and c,
    but a partial function over it might only be interested in parameters a and c.

    Upon invocation of a partial function, the input arguments are filtered to leave
    only those that are of interest to the partial function.
    This is done using the argument names specified by the base function (via self._base_function.args)
    and the args of the partial function (self.args).
    """

    def __init__(self, function, base_function, args=None):
        super(_PartialFunction, self).__init__(function, args)
        self._base_function = base_function

    def __call__(self, *args, **kwargs):
        partial_args = self._find_arg_values(args)
        partial_kwargs = {k: v for k, v in kwargs.iteritems() if k in self.args}
        return self._function(*partial_args, **partial_kwargs)

    def _find_arg_values(self, input_arg_values):
        unnecessary_arg_names = set(self._base_function.args) - set(self.args)
        unnecessary_arg_indexes = [self._base_function.args.index(arg_name) for arg_name in unnecessary_arg_names]
        return [arg_value for index, arg_value in enumerate(input_arg_values)
                if index not in unnecessary_arg_indexes]
