from polyfuncs import generic


@generic
def f(a):
    return 'default'


@f.when(int)
def _(a):
    return 'int'

@f.when(str)
def _(a):
    return 'str'

@f.when(lambda a: len(a) >= 10)
def _(a):
    return 'len(n) > 10'




print f(1)
print f('aaa')
print f([])
print f('bbbbbbbbbbbb')
