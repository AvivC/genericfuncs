from __future__ import unicode_literals, division, print_function, absolute_import

import collections
import inspect


class generic(object):
    def __init__(self, generic_function):
        self._wrapped = generic_function
        self._base_args = _BaseArgs.from_function(generic_function)
        self._predicates_and_functions = []

    def __call__(self, *args, **kwargs):
        for predicate_info, function_info in self._predicates_and_functions:
            predicate_args, predicate_kwargs = \
                self._base_args.find_args_for_arg_filtered_function(predicate_info.args, args, kwargs)
            if predicate_info.function(*predicate_args, **predicate_kwargs):
                function_args, function_kwargs = \
                    self._base_args.find_args_for_arg_filtered_function(function_info.args, args, kwargs)
                return function_info.function(*function_args, **function_kwargs)

        return self._wrapped(*args, **kwargs)

    def when(self, predicate):
        def decorator(function):
            predicate_info = self._base_args.make_function_info(predicate)
            function_info = self._base_args.make_function_info(function)

            if not self._all_params_valid(predicate_info):
                raise ValueError('Argument specified in predicate doesn\'t exist in base function.')
            if not self._all_params_valid(function_info):
                raise ValueError('Argument specified in implementation doesn\'t exist in base function.')

            self._predicates_and_functions.append((predicate_info, function_info))
            return function
        return decorator

    def _all_params_valid(self, function_info):
        return all(arg in self._base_args._args for arg in function_info.args)


class _BaseArgs(object):
    def __init__(self, args):
        if not isinstance(args, collections.Sequence):
            raise TypeError('args must be a sequence.')
        self._args = args if isinstance(args, tuple) else tuple(args)

    @staticmethod
    def from_function(func):
        args = func.__code__.co_varnames[:func.__code__.co_argcount]
        if inspect.ismethod(func):
            args = args[1:]  # strip self arg
        return _BaseArgs(args)

    def make_function_info(self, function_source):
        if isinstance(function_source, collections.Callable):
            return self._make_function_info_from_callable(function_source)

        # this check must appear before the Iterable check, because dicts are iterables
        elif isinstance(function_source, dict):
            return self._make_function_info_from_dict(function_source)

        elif isinstance(function_source, collections.Iterable):
            return self._make_function_info_from_iterable(function_source)

        else:
            raise TypeError('Input to when() is not a callable, a dict or an iterable of callables.')

    def _make_function_info_from_dict(self, function_source):
        def predicate(*args, **kwargs):
            for arg_name, arg_predicate_source in function_source.iteritems():
                arg_predicate_base_args = _BaseArgs([arg_name])
                arg_predicate_info = arg_predicate_base_args.make_function_info(arg_predicate_source)
                arg_value = self.get_arg_value(arg_name, args, kwargs)
                if not arg_predicate_info.function(arg_value):
                    return False
            return True

        return _FunctionInfo(predicate, self._args)

    def _make_function_info_from_callable(self, function_source):
        if inspect.isfunction(function_source) or inspect.ismethod(function_source):
            args = function_source.__code__.co_varnames[:function_source.__code__.co_argcount]
            if inspect.ismethod(function_source):
                args = args[1:]  # strip self arg
            return _FunctionInfo(function_source, args)

        elif inspect.isclass(function_source):
            desired_type = function_source

            def type_checker(*args, **kwargs):
                return all(isinstance(arg, desired_type) for arg in args) \
                       and all(isinstance(v, desired_type) for k, v in kwargs.iteritems())

            return _FunctionInfo(type_checker, self._args)

        else:
            # strip self arg
            args = function_source.__call__.__code__.co_varnames[:function_source.__call__.__code__.co_argcount][1:]
            return _FunctionInfo(function_source.__call__, args)

    def _make_function_info_from_iterable(self, function_source):
        predicate_infos = map(self.make_function_info, function_source)

        def composed_predicates(*args, **kwargs):
            for predicate_info in predicate_infos:
                predicate_args, predicate_kwargs = \
                    self.find_args_for_arg_filtered_function(predicate_info.args, args, kwargs)
                if not predicate_info.function(*predicate_args, **predicate_kwargs):
                    return False
            return True

        return _FunctionInfo(composed_predicates, self._args)

    def get_arg_value(self, arg_name, input_args, input_kwargs):
        try:
            return input_kwargs[arg_name]
        except KeyError:
            pass
        try:
            arg_index = self._args.index(arg_name)
            return input_args[arg_index]
        except IndexError:
            raise ValueError('Specified argument doesn\'t exist in generic function.')

    def find_args_for_arg_filtered_function(self, wanted_arg_names, input_arg_values, input_kwarg_values):
        wanted_arg_indexes = [self._args.index(arg_name) for arg_name in wanted_arg_names]
        arg_values = [arg_value for index, arg_value in enumerate(input_arg_values)
                      if index in wanted_arg_indexes]
        kwarg_values = {k: v for k, v in input_kwarg_values.iteritems() if k in self._args}

        return arg_values, kwarg_values

    def __getitem__(self, key):
        return self._args[key]

    def __len__(self):
        return len(self._args)

    def __iter__(self):
        return iter(self._args)

    def __reversed__(self):
        return _BaseArgs(reversed(self._args))

# _FunctionInfo = collections.namedtuple('_FunctionInfo', ['function', 'args'])


class _FunctionInfo(object):
    def __init__(self, function, args=None):
        self.function = function

        if args is not None:
            self.args = args
        else:
            self.args = function.__code__.co_varnames[:function.__code__.co_argcount]
            if inspect.ismethod(function):
                self.args = self.args[1:]  # strip self arg

# class _ArgInjectedFunction(object)
#     def __init__(self):
