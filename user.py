from genericfuncs import generic


@generic
def f(a):
    return 'default'


@f.when(lambda a: True)
def _(a):
    return


f(a=8)
