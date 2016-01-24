import genericfuncs


@genericfuncs.generic
def genfunc(a, b):
    return 'default'


@genfunc.when({
    'b': basestring
})
def _(a, b):
    return 'b is a basestring'


assert genfunc(10, 'abc') == 'b is a basestring'
