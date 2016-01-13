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
            predicate_args = self._get_arg_values_for_partial_func(args, predicate.args)
            if predicate(*predicate_args):
                impl_arg = self._get_arg_values_for_partial_func(args, func.args)
                return func(*impl_arg)
        return self._default_impl(*args, **kwargs)

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
                predicate_input = self._get_arg_values_for_partial_func(args, predicate.args)
                if not predicate(*predicate_input):
                    return False
            return True

        predicate_info = _FunctionInfo(composed_predicates)
        predicate_info.args = self._default_impl.args
        return predicate_info

    def _get_arg_values_for_partial_func(self, input_arg_values, partial_func_args):
            return [input_arg_values[self._default_impl.args.index(arg_name)] for arg_name in partial_func_args]

    def _all_params_valid(self, function_info):
        return all(arg in self._default_impl.args for arg in function_info.args)


_PredicateFunctionMappping = namedtuple('PredicateFunctionMappping', ['predicate_info', 'func_info'])


class _FunctionInfo(object):
    def __init__(self, function):
        self.function = function
        self.args = inspect.getargspec(function).args

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)
