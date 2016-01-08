class generic(object):
    def __init__(self, wrapped):
        self._default_impl = wrapped
        self._predicates_and_funcs = []

    def __call__(self, *args, **kwargs):
        pass

    def when(self, predicate):
        def dec(func):
            self._predicates_and_funcs.append((predicate, func))
            return func
        
