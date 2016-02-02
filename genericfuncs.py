from __future__ import unicode_literals, division, print_function, absolute_import

import collections
import inspect


class generic(object):
    def __init__(self, generic_function):
        self._wrapped_function_info = _FunctionInfo(generic_function)
        self._predicate_factory = _PredicateFactory.over_function(generic_function)
        self._predicates_and_functions = []

    def __call__(self, *args, **kwargs):
        for predicate, function in self._predicates_and_functions:
            if predicate(*args, **kwargs):
                return function(*args, **kwargs)

        return self._wrapped_function_info(*args, **kwargs)

    def when(self, predicate_source):
        def decorator(function):
            predicate = self._predicate_factory.make_predicate(predicate_source)
            function = _ArgInjector.from_callable(function, self._wrapped_function_info.args)

            if not self._all_params_valid(predicate.function_info):
                raise ValueError('Argument specified in predicate doesn\'t exist in base function.')
            if not self._all_params_valid(function.function_info):
                raise ValueError('Argument specified in implementation doesn\'t exist in base function.')

            self._predicates_and_functions.append((predicate, function))
            return function
        return decorator

    def _all_params_valid(self, function_info):
        return all(arg in self._wrapped_function_info.args for arg in function_info.args)


class _PredicateFactory(object):
    def __init__(self, args):
        if not isinstance(args, collections.Sequence):
            raise TypeError('args must be a sequence.')
        self._base_args = args if isinstance(args, tuple) else tuple(args)

    @staticmethod
    def over_function(func):
        args = func.__code__.co_varnames[:func.__code__.co_argcount]
        if inspect.ismethod(func):
            args = args[1:]  # strip self arg
        return _PredicateFactory(args)

    def make_predicate(self, function_source):
        if isinstance(function_source, collections.Callable):
            return _ArgInjector.from_callable(function_source, self._base_args)

        # this check must appear before the Iterable check, because dicts are iterables
        elif isinstance(function_source, dict):
            return self._make_from_dict(function_source)

        elif isinstance(function_source, collections.Iterable):
            return self._make_from_iterable(function_source)

        else:
            raise TypeError('Input to when() is not a callable, a dict or an iterable of callables.')

    def _make_from_dict(self, function_source):
        def predicate(*args, **kwargs):
            for arg_name, arg_predicate_source in function_source.iteritems():
                arg_predicate_factory = _PredicateFactory([arg_name])
                arg_predicate = arg_predicate_factory.make_predicate(arg_predicate_source)
                arg_value = self.get_arg_value(arg_name, args, kwargs)
                if not arg_predicate(arg_value):
                    return False
            return True

        return _ArgInjector(predicate, self._base_args)

    def _make_from_callable(self, function_source):
        if inspect.isfunction(function_source) or inspect.ismethod(function_source):
            return _ArgInjector(function_source, self._base_args)

        elif inspect.isclass(function_source):
            desired_type = function_source

            def type_checker(*args, **kwargs):
                return all(isinstance(arg, desired_type) for arg in args) \
                       and all(isinstance(v, desired_type) for k, v in kwargs.iteritems())

            return _ArgInjector(type_checker, self._base_args)

        else:
            return _ArgInjector(function_source.__call__, self._base_args)

    def _make_from_iterable(self, function_source):
        predicates = map(self.make_predicate, function_source)

        def composed_predicates(*args, **kwargs):
            for predicate in predicates:
                if not predicate(*args, **kwargs):
                    return False
            return True

        return _ArgInjector(composed_predicates, self._base_args)

    def get_arg_value(self, arg_name, input_args, input_kwargs):
        try:
            return input_kwargs[arg_name]
        except KeyError:
            pass
        try:
            arg_index = self._base_args.index(arg_name)
            return input_args[arg_index]
        except IndexError:
            raise ValueError('Specified argument doesn\'t exist in generic function.')

    def find_args_for_arg_filtered_function(self, wanted_arg_names, input_arg_values, input_kwarg_values):
        wanted_arg_indexes = [self._base_args.index(arg_name) for arg_name in wanted_arg_names]
        arg_values = [arg_value for index, arg_value in enumerate(input_arg_values)
                      if index in wanted_arg_indexes]
        kwarg_values = {k: v for k, v in input_kwarg_values.iteritems() if k in self._base_args}

        return arg_values, kwarg_values

    def __getitem__(self, key):
        return self._base_args[key]

    def __len__(self):
        return len(self._base_args)

    def __iter__(self):
        return iter(self._base_args)

    def __reversed__(self):
        return _PredicateFactory(reversed(self._base_args))


class _FunctionInfo(object):
    def __init__(self, function, args=None):
        self.function = function

        if args is not None:
            self.args = args
        else:
            self.args = function.__code__.co_varnames[:function.__code__.co_argcount]
            if inspect.ismethod(function):
                self.args = self.args[1:]  # strip self arg

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)


class _ArgInjector(object):
    def __init__(self, function, base_args):
        self.function_info = _FunctionInfo(function)
        self._base_args = base_args

    @staticmethod
    def from_callable(callable, base_args):
        if inspect.isfunction(callable) or inspect.ismethod(callable):
            return _ArgInjector(callable, base_args)

        elif inspect.isclass(callable):
            desired_type = callable

            def type_checker(*args, **kwargs):
                return all(isinstance(arg, desired_type) for arg in args) \
                       and all(isinstance(v, desired_type) for k, v in kwargs.iteritems())

            return _ArgInjector(type_checker, base_args)

        else:
            return _ArgInjector(callable.__call__, base_args)

    def __call__(self, *args, **kwargs):
        wanted_arg_indexes = [self.function_info.args.index(arg_name) for arg_name in self.function_info.args]
        arg_values = [arg_value for index, arg_value in enumerate(args)
                      if index in wanted_arg_indexes]
        kwarg_values = {k: v for k, v in kwargs.iteritems() if k in self.function_info.args}

        return self.function_info(*arg_values, **kwarg_values)
