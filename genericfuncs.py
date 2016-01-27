from __future__ import unicode_literals, division, print_function, absolute_import

import collections
import inspect

class generic(object):
    def __init__(self, generic_function):
        self._generic_func_info = self._make_function_info(generic_function)
        self._predicates_and_functions = []

    def __call__(self, *args, **kwargs):
        for predicate_info, function_info in self._predicates_and_functions:
            predicate_args, predicate_kwargs = \
                self._find_args_for_arg_filtered_function(self._generic_func_info.args, predicate_info.args, args, kwargs)
            if predicate_info.function(*predicate_args, **predicate_kwargs):
                function_args, function_kwargs = \
                    self._find_args_for_arg_filtered_function(self._generic_func_info.args, function_info.args, args, kwargs)
                return function_info.function(*function_args, **function_kwargs)

        return self._generic_func_info.function(*args, **kwargs)

    def when(self, predicate):
        def decorator(function):
            predicate_info = self._make_function_info(predicate)
            function_info = self._make_function_info(function)

            if not self._all_params_valid(predicate_info):
                raise ValueError('Argument specified in predicate doesn\'t exist in base function.')
            if not self._all_params_valid(function_info):
                raise ValueError('Argument specified in implementation doesn\'t exist in base function.')

            self._predicates_and_functions.append((predicate_info, function_info))
            return function
        return decorator

    def _find_args_for_arg_filtered_function(self, full_arg_names, wanted_arg_names,
                                             input_arg_values, input_kwarg_values):
        wanted_arg_indexes = [full_arg_names.index(arg_name) for arg_name in wanted_arg_names]
        arg_values = [arg_value for index, arg_value in enumerate(input_arg_values)
                      if index in wanted_arg_indexes]
        kwarg_values = {k: v for k, v in input_kwarg_values.iteritems() if k in self._generic_func_info.args}

        return arg_values, kwarg_values

    def _all_params_valid(self, function_info):
        return all(arg in self._generic_func_info.args for arg in function_info.args)

    def _make_function_info(self, function_source):
        if isinstance(function_source, collections.Callable):
            args, function = self._make_function_info_from_callable(function_source)
        elif isinstance(function_source, collections.Iterable):
            args, function = self._make_function_info_from_iterable(function_source)
        else:
            raise TypeError('Input to when() is not a callable, a dict or an iterable of callables.')

        return _FunctionInfo(function, args)

    def _make_function_info_from_callable(self, function_source):
        if inspect.isfunction(function_source) or inspect.ismethod(function_source):
            args = function_source.__code__.co_varnames[:function_source.__code__.co_argcount]
            if inspect.ismethod(function_source):
                args = args[1:]  # strip self arg
            function = function_source
        elif inspect.isclass(function_source):
            desired_type = function_source
            args = self._generic_func_info.args

            def type_checker(*args, **kwargs):
                return all(isinstance(arg, desired_type) for arg in args) \
                       and all(isinstance(v, desired_type) for k, v in kwargs.iteritems())

            function = type_checker
        else:
            function = function_source.__call__
            args = function.__code__.co_varnames[:function.__code__.co_argcount][1:]  # strip self arg
        return args, function

    def _make_function_info_from_iterable(self, function_source):
        predicate_infos = map(self._make_function_info, function_source)

        def composed_predicates(*args, **kwargs):
            for predicate_info in predicate_infos:
                predicate_args, predicate_kwargs = \
                    self._find_args_for_arg_filtered_function(self._generic_func_info.args, predicate_info.args, args, kwargs)
                if not predicate_info.function(*predicate_args, **predicate_kwargs):
                    return False
            return True

        function = composed_predicates
        args = self._generic_func_info.args
        return args, function


_FunctionInfo = collections.namedtuple('_FunctionInfo', ['function', 'args'])
