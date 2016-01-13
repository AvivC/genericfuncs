from polyfuncs import generic


@generic
def f(a, b, c):
    return [a, b, c]


@f.when(lambda a, b, c: True)
def _(b, c):
    return [b, c]


print f(1, 2, 3, c=3)
