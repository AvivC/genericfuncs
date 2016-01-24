from __future__ import unicode_literals
from __future__ import division

import pytest
import genericfuncs


def test_genfunc_with_only_default_impl():
    @genericfuncs.generic
    def genfunc(n):
        return n * 2
    assert genfunc(4) == 8
    assert genfunc(n=4) == 8


def test_correct_genfunc_impl_invoked():
    @genericfuncs.generic
    def genfunc(a, b, c):
        return 'default impl'

    @genfunc.when(lambda a, b, c: a > b > c)
    def when_a_largerthan_b_largerthan_c(a, b, c):
        return 'a > b > c'

    @genfunc.when(long)
    def when_all_params_long(a, b, c):
        return 'all are long'

    @genfunc.when(lambda a, b, c: a < b < c)
    def when_a_lessthan_b_lessthan_c(a, b, c):
        return 'a < b < c'

    class C1(object):
        def predicate(self, a, b, c):
            return a * b * c == 0

    @genfunc.when(C1().predicate)
    def when_one_or_more_params_is_zero(a, b, c):
        return 'one or more is 0'

    class C2(object):
        def __call__(self, a, b, c):
            return a == b == c == 8

    @genfunc.when(C2())
    def when_all_equal_eight(a, b, c):
        return 'a == b == c == 8'

    assert genfunc(4, 4, 4) == 'default impl'
    assert genfunc(5, 3, 2) == 'a > b > c'
    assert genfunc(10L, 20L, 1L) == 'all are long'
    assert genfunc(1, 10, 30) == 'a < b < c'
    assert genfunc(2, 10, 0) == 'one or more is 0'
    assert genfunc(8, 8, 8) == 'a == b == c == 8'


def test_invalid_predicate_raises_exception():
    @genericfuncs.generic
    def genfunc(n):
        return n * 2

    with pytest.raises(TypeError):
        @genfunc.when(10)
        def impl(n):
            return 'should never run'


def test_parameter_injection():
    @genericfuncs.generic
    def genfunc(a, b, c, d):
        return locals()

    @genfunc.when(lambda a, b, c, d: a == 1 and b == 2 and c == 3 and d == 4)
    def _(a, b, c, d):
        return locals()

    @genfunc.when(lambda a, b, c: a == 1 and b == 2 and c == 3 and 'd' not in locals())
    def _(a, b, c):
        return locals()

    @genfunc.when(lambda b, c, d: 'a' not in locals() and b == 1 and c == 2 and d == 3)
    def _(b, c, d):
        return locals()

    @genfunc.when(lambda b, c: 'a' not in locals() and b == 1 and c == 2 and 'd' not in locals())
    def _(b, c):
        return locals()

    assert genfunc(1, 2, 3, 4) == {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    assert genfunc(1, 2, 3, 0) == {'a': 1, 'b': 2, 'c': 3}
    assert genfunc(0, 1, 2, 3) == {'b': 1, 'c': 2, 'd': 3}
    assert genfunc(0, 1, 2, 0) == {'b': 1, 'c': 2}
    assert genfunc(0, 0, 0, 0) == {'a': 0, 'b': 0, 'c': 0, 'd': 0}

    with pytest.raises(ValueError) as exc_info:
        @genfunc.when(lambda a, b, c, d, e: True)
        def _(b, c):
            return locals()
    assert "Argument specified in predicate doesn\'t exist in base function." in str(exc_info)

    with pytest.raises(ValueError) as exc_info:
        @genfunc.when(lambda a, b, c, d: True)
        def _(b, c, e):
            return locals()
    assert "Argument specified in implementation doesn\'t exist in base function." in str(exc_info)


def test_multiple_predicates():
    @genericfuncs.generic
    def genfunc(a, b, c):
        return 'default'

    @genfunc.when([lambda a, b, c: a == 10 and b == 20 and c == 30, lambda a, b, c: c > b > a])
    def _(a, b, c):
        return locals()

    @genfunc.when([lambda b: b == 50, lambda a, c: c > a])
    def _(a, b, c):
        return locals()

    @genfunc.when([lambda b: b == 60, lambda a, c: c > a])
    def _(c):
        return locals()

    @genfunc.when([lambda b: b == 'paramb', lambda a, c: a == 'parama' and c == 'paramc', basestring])
    def _(c):
        return locals()

    @genfunc.when([float, int])  # should never run
    def _(a, b, c):
        return locals()

    assert genfunc(10, 20, 30) == {'a': 10, 'b': 20, 'c': 30}
    assert genfunc(10, 50, 30) == {'a': 10, 'b': 50, 'c': 30}
    assert genfunc(10, 60, 30) == {'c': 30}
    assert genfunc('parama', 'paramb', 'paramc') == {'c': 'paramc'}
    assert genfunc(10, 1.5, 5) == 'default'


def test_genfunc_call_with_keyword_arguments():
    @genericfuncs.generic
    def genfunc(a, b, c):
        return 'default'

    @genfunc.when(lambda a, b, c: a > b > c)
    def _(a, b, c):
        return [a, b, c]

    assert genfunc(1, 1, 1) == 'default'
    assert genfunc(a=1, b=1, c=1) == 'default'
    assert genfunc(1, 1, c=1) == 'default'
    assert genfunc(1, b=1, c=1) == 'default'
    with pytest.raises(TypeError) as exc_info:
        genfunc(1, 1, 1, c=1)
    assert 'got multiple values for keyword argument' in str(exc_info)
    with pytest.raises(TypeError) as exc_info:
        genfunc(1, 1, 1, b=1, c=1)
    assert 'got multiple values for keyword argument' in str(exc_info)

    assert genfunc(3, 2, 1) == [3, 2, 1]
    assert genfunc(a=3, b=2, c=1) == [3, 2, 1]
    assert genfunc(3, 2, c=1) == [3, 2, 1]
    with pytest.raises(TypeError) as exc_info:
        genfunc(3, 2, 1, b=2, c=1)
    assert 'got multiple values for keyword argument' in str(exc_info)


def test_invalid_genfunc_calls_raise_error():
    @genericfuncs.generic
    def genfunc(a, b, c):
        return 'default'

    with pytest.raises(ValueError) as exc_info:
        genfunc(1, 2, 3, 4)
    assert 'Received too many positional arguments.' in str(exc_info)

    with pytest.raises(ValueError) as exc_info:
        genfunc(1, 2, d=3)
    assert 'One or more keyword arguments don\'t exist in the generic function.' in str(exc_info)


def test_predicates_with_type_precondition_all_same_type():
    @genericfuncs.generic
    def genfunc(a):
        return 'default'

    @genfunc.when(lambda a: a > 5, type=int)
    def _(a):
        return 'a > 5'

    @genfunc.when(lambda a: a < 5, type=int)
    def _(a):
        return 'a < 5'

    assert genfunc(6) == 'a > 5'
    assert genfunc(4) == 'a < 5'
    assert genfunc(5) == 'default'


def test_predicates_with_type_precondition_different_types():
    # normally in Python, trying to evaluate the first predicate here - `lambda a: a % 2 == 0` -
    # where type(a) is unicode, would raise a TypeError and crash the program.
    # obviously that's because unicode doesn't support operator %.

    # however here, when encountering the first predicate, an exception should not be raised.
    # this is because before running the predicate, the precondition created by specifying `type=int` is checked.
    # if it is False, the predicate is never run, and a TypeError is never raised.
    # this is the point of having the `type=something` option.

    # the `type` optional parameter should be used when predicates that expect different types are specified.

    @genericfuncs.generic
    def genfunc(a):
        return 'default'

    @genfunc.when(lambda a: a % 2 == 0, type=[int, float])
    def _(a):
        return 'a % 2 == 0'

    @genfunc.when(lambda a: a.startswith('bar'))
    def _(a):
        return 'a.startswith(\'bar\')'

    @genfunc.when(lambda a: a.endswith('foo'), type=basestring)
    def _(a):
        return 'a.endswith(\'foo\')'

    assert genfunc(8) == 'a % 2 == 0'
    assert genfunc(8.0) == 'a % 2 == 0'
    # pytest.set_trace()
    assert genfunc(a=8) == 'a % 2 == 0'

    assert genfunc('abcfoo') == 'a.endswith(\'foo\')'
    assert genfunc(a='abcfoo') == 'a.endswith(\'foo\')'

    with pytest.raises(AttributeError):
        genfunc(5)   # an AttributeError should be raised inside the second predicate (`a.startswith('bar')`),
                     # because int objects don't have the `startswith` methodd.
                     # the predicate is allowed to run, because `type=basestring` wasn't specified.

    assert genfunc('abc') == 'default'


def test_type_precondition_as_dict():
    @genericfuncs.generic
    def genfunc(a, b):
        return 'default'

    @genfunc.when(lambda a, b: a > b, type={'a': int, 'b': int})
    def _(a):
        return 'a > b'

    @genfunc.when(lambda b: b.endswith('bar'), type={'b': basestring})
    def _(a):
        return 'b.endswith(\'bar\')'

    @genfunc.when(lambda a, b: len(a) == b, type={'a': [list, tuple], 'b': int})
    def _(a):
        return 'len(a) == b'

    assert genfunc(15, 10) == 'a > b'
    assert genfunc(15, b=10) == 'a > b'
    assert genfunc(a=15, b=10) == 'a > b'

    assert genfunc('aaa', 'blabar') == 'b.endswith(\'bar\')'
    assert genfunc('aaa', b='blabar') == 'b.endswith(\'bar\')'
    assert genfunc(a='aaa', b='blabar') == 'b.endswith(\'bar\')'

    assert genfunc([1, 2, 3], 3) == 'len(a) == b'
    assert genfunc((1, 2, 3), 3) == 'len(a) == b'
    assert genfunc((1, 2, 3), b=3) == 'len(a) == b'
    assert genfunc(a=(1, 2, 3), b=3) == 'len(a) == b'

    assert genfunc(5, 5) == 'default'
    assert genfunc('', b='abc') == 'default'
    assert genfunc(a='', b='abc') == 'default'
    assert genfunc([], {}) == 'default'
    assert genfunc([1, 2, 3], 4) == 'default'

    with pytest.raises(TypeError) as exc_info:
        @genfunc.when(lambda a, b: True, type={'a': int, 'b': lambda b: ''})
        def _(a, b):
            return ''
    assert 'In a dict that maps arguments to expected types, the values must be either types or iterables of types.' \
           in str(exc_info)


def test_dict_as_predicate():
    @genericfuncs.generic
    def genfunc(a, b):
        return 'default'

    @genfunc.when({
        'a': lambda a: a == 5,
        'b': lambda b: b == 10
    })
    def _(a, b):
        return 'a == 5 and b == 10'

    @genfunc.when({
        'b': int
    })
    def _(a, b):
        return 'b is an int'

    @genfunc.when({
        'a': [int, lambda a: a % 2 == 0, lambda a: a > 20]
    })
    def _(a, b):
        return 'a is divisibe by 2 and greater than 20'

    @genfunc.when({
        'a': lambda a: a.startswith('foo')
    }, type=basestring)
    def _(a, b):
        return 'a starts with foo and all args are strings'

    @genfunc.when({
        'a': lambda a: a.startswith('foo')
    }, type={
        'a': basestring,
        'b': float
    })
    def _(a, b):
        return 'a starts with foo, a is a string and b is a float'

    # not currently supported
    # @genfunc.when({
    #     'a': lambda a: a.startswith('foo')
    # }, type=[basestring, list])
    # def _(a, b):
    #     return 'a starts with foo and all are either strings or lists'

    assert genfunc(5, 10) == 'a == 5 and b == 10'
    assert genfunc('bla', b=12) == 'b is an int'
    assert genfunc(a='bla', b=12) == 'b is an int'
    assert genfunc(5, 15) == 'b is an int'
    assert genfunc(30, 'bla') == 'a is divisibe by 2 and greater than 20'
    assert genfunc('foobla', 'bla') == 'a starts with foo and all args are strings'
    # not currently supported
    # assert genfunc('foobla', []) == 'a starts with foo and all are either strings or lists'
    assert genfunc([], []) == 'default'
    assert genfunc([], b=[]) == 'default'
    assert genfunc(a=[], b=[]) == 'default'


