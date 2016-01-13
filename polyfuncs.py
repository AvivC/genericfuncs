import collections
import inspect
from collections import namedtuple
import functools


class generic(object):
    def __init__(self, wrapped):
        self._default_impl = _FunctionInfo(wrapped)
        self._predicates_and_funcs = []
        functools.update_wrapper(self, wrapped)

    def __call__(self, *args, **kwargs):
        for predicate, func in self._predicates_and_funcs:
            predicate_arg_values = _match_arg_values_for_partial_func(args, self._default_impl.args, predicate.args)
            if predicate(*predicate_arg_values):
                impl_arg_values = _match_arg_values_for_partial_func(args, self._default_impl.args, func.args)
                return func(*impl_arg_values)
        return self._default_impl(*args, **kwargs)

    def when(self, predicate):
        if not isinstance(predicate, collections.Callable):
            raise TypeError('Predicate isn\'t a callable.')

        def dec(func):
            predicate_info = _FunctionInfo(predicate)
            impl_info = _FunctionInfo(func)

            if not self._all_params_valid(predicate_info):
                raise ValueError('Argument specified in predicate doesn\'t exist in base function.')
            if not self._all_params_valid(impl_info):
                raise ValueError('Argument specified in implementation doesn\'t exist in base function.')

            self._predicates_and_funcs.append(_PredicateFunctionMappping(predicate_info, impl_info))
            return func

        return dec

    def _all_params_valid(self, function_info):
        return all(arg in self._default_impl.args for arg in function_info.args)


def _match_arg_values_for_partial_func(input_arg_values, base_func_args, partial_func_args):
    return [input_arg_values[base_func_args.index(arg_name)] for arg_name in partial_func_args]

_PredicateFunctionMappping = namedtuple('PredicateFunctionMappping', ['predicate_info', 'func_info'])


class _FunctionInfo(object):
    def __init__(self, function):
        self.function = function
        self.args = inspect.getargspec(function).args

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)
