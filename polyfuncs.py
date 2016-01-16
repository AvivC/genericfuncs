from __future__ import unicode_literals, division, print_function, absolute_import

import collections
import inspect
from collections import namedtuple
import functools


class generic(object):
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
