from polyfuncs import generic


@generic(by_name=False)
def f(a, b, c, d):
    return a * b * c * d


@f.when(lambda a: a > 20)
def _(a, b, c):
    pass