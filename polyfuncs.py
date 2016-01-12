import collections
import inspect


class generic(object):
    def __init__(self, wrapped):
        self._default_impl = _PredicateInfo(wrapped)
        self._predicates_and_funcs = []

    def __call__(self, *predicate_args, **kwargs):
        for predicate_info, func in self._predicates_and_funcs:
            if predicate_info.predicate(*predicate_args, **kwargs):
                return func(*predicate_args, **kwargs)
        return self._default_impl.predicate(*predicate_args, **kwargs)

    def when(self, predicate):
        if not isinstance(predicate, collections.Callable):
            raise TypeError('Predicate isn\'t a callable.')

        def dec(func):
            predicate_info = _PredicateInfo(predicate)
            self._predicates_and_funcs.append((predicate_info, func))
            return func
        return dec


class _PredicateInfo(object):
    def __init__(self, predicate):
        self.predicate = predicate
        self.args = inspect.getargspec(predicate).args
