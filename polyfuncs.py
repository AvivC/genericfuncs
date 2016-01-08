from collections import Callable


class generic(object):
    def __init__(self, wrapped):
        self._default_impl = wrapped
        self._predicates_and_funcs = []

    def __call__(self, *args, **kwargs):
        for predicate, func in self._predicates_and_funcs:
            if predicate(*args, **kwargs):
                return func(*args, **kwargs)
        return self._default_impl(*args, **kwargs)

    def when(self, predicate):
        if not isinstance(predicate, Callable):
            raise TypeError('Predicate isn\'t a callable.')

        def dec(func):
            self._predicates_and_funcs.append((predicate, func))
            return func
        return dec
