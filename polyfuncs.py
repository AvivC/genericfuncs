from __future__ import unicode_literals
from __future__ import division

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
        self._validate_args(args, kwargs)  # should probably do a more 'native-python' solution later

        for predicate, func in self._predicates_and_funcs:
            predicate_args, predicate_kwargs = self._get_arg_and_kwarg_values_for_partial_func(predicate.args, args,
                                                                                               kwargs)
            if predicate(*predicate_args, **predicate_kwargs):
                impl_args, impl_kwargs = self._get_arg_and_kwarg_values_for_partial_func(func.args, args, kwargs)
                return func(*impl_args, **impl_kwargs)
        return self._base_func(*args, **kwargs)

    def _validate_args(self, args, kwargs):
        if any(kwarg not in self._base_func.args for kwarg in kwargs):
            raise ValueError('One or more keyword arguments don\'t exist in the generic function.')
        if len(args) > len(self._base_func.args):
            raise ValueError('Received too many positional arguments.')

    def when(self, predicate):
        if isinstance(predicate, collections.Iterable):
            predicate_info = self._compose_predicates(predicate)
        elif isinstance(predicate, collections.Callable):
            predicate_info = _FunctionInfo(predicate)
        else:
            raise TypeError('Input to when() is not a callable nor an iterable of callables.')

        def dec(func):
            impl_info = _FunctionInfo(func)

            if not self._all_params_valid(predicate_info):
                raise ValueError('Argument specified in predicate doesn\'t exist in base function.')
            if not self._all_params_valid(impl_info):
                raise ValueError('Argument specified in implementation doesn\'t exist in base function.')

            self._predicates_and_funcs.append(_PredicateFunctionMappping(predicate_info, impl_info))
            return func

        return dec

    def _compose_predicates(self, predicates):
        predicate_infos = map(_FunctionInfo, predicates)

        def composed_predicates(*args, **kwargs):
            for predicate in predicate_infos:
                predicate_args, predicate_kwargs = self._get_arg_and_kwarg_values_for_partial_func(predicate.args, args,
                                                                                                   kwargs)
                if not predicate(*predicate_args, **predicate_kwargs):
                    return False
            return True

        predicate_info = _FunctionInfo(composed_predicates)
        predicate_info.args = self._base_func.args
        return predicate_info

    def _get_arg_and_kwarg_values_for_partial_func(self, partial_func_arg_names, input_arg_values, input_kwargs):
        partial_args = self._find_partial_arg_values(input_arg_values, partial_func_arg_names)
        partial_kwargs = {k: v for k, v in input_kwargs.iteritems() if k in partial_func_arg_names}
        return partial_args, partial_kwargs

    def _find_partial_arg_values(self, input_arg_values, partial_func_arg_names):
        unnecessary_arg_names = set(self._base_func.args) - set(partial_func_arg_names)
        unnecessary_arg_indexes = [self._base_func.args.index(arg_name) for arg_name in unnecessary_arg_names]
        return [arg_value for index, arg_value in enumerate(input_arg_values)
                if index not in unnecessary_arg_indexes]

    def _all_params_valid(self, function_info):
        return all(arg in self._base_func.args for arg in function_info.args)


_PredicateFunctionMappping = namedtuple('PredicateFunctionMappping', ['predicate_info', 'func_info'])


class _FunctionInfo(object):
    def __init__(self, function):
        self.function = function
        self.args = inspect.getargspec(function).args

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)
