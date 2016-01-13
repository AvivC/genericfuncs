from __future__ import unicode_literals
from __future__ import division

import pytest
import polyfuncs


def test_genfunc_with_only_default_impl():
    @polyfuncs.generic
    def genfunc(n):
        return n * 2
    assert genfunc(4) == 8
    assert genfunc(n=4) == 8


def test_single_param_genfunc_correct_impl_invoked():
    @polyfuncs.generic
    def genfunc(n):
        return n * 2

    @genfunc.when(lambda n: n > 10)
    def when_n_largerthan_10(n):
        return 'n > 10'

    @genfunc.when(lambda n: n < -5)
    def when_n_smallerthan_minus_5(n):
        return 'n < -5'

    assert genfunc(5) == 10
    assert genfunc(10) == 20
    assert genfunc(15) == 'n > 10'
    assert genfunc(-5) == -10
    assert genfunc(-7) == 'n < -5'


def test_multiple_params_genfunc_correct_impl_invoked():
    @polyfuncs.generic
    def genfunc(a, b, c):
        return 'default impl'

    @genfunc.when(lambda a, b, c: a > b > c)
    def when_a_largerthan_b_largerthan_c(a, b, c):
        return 'a > b > c'

    @genfunc.when(lambda a, b, c: a < b < c)
    def when_a_lessthan_b_lessthan_c(a, b, c):
        return 'a < b < c'

    assert genfunc(4, 4, 4) == 'default impl'
    assert genfunc(5, 3, 2) == 'a > b > c'
    assert genfunc(1, 10, 30) == 'a < b < c'


def test_invalid_predicate_raises_exception():
    @polyfuncs.generic
    def genfunc(n):
        return n * 2

    with pytest.raises(TypeError):
        @genfunc.when(10)
        def impl(n):
            return 'should never run'


def test_parameter_injection():
    @polyfuncs.generic
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
    @polyfuncs.generic
    def genfunc(a, b, c):
        pass

    @genfunc.when([lambda a, b, c: a == 10 and b == 20 and c == 30, lambda a, b, c: c > b > a])
    def _(a, b, c):
        return locals()

    @genfunc.when([lambda b: b == 50, lambda a, c: c > a])
    def _(a, b, c):
        return locals()

    @genfunc.when([lambda b: b == 60, lambda a, c: c > a])
    def _(c):
        return locals()

    assert genfunc(10, 20, 30) == {'a': 10, 'b': 20, 'c': 30}
    assert genfunc(10, 50, 30) == {'a': 10, 'b': 50, 'c': 30}
    assert genfunc(10, 60, 30) == {'c': 30}


def test_genfunc_call_with_keyword_arguments():
    @polyfuncs.generic
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
    @polyfuncs.generic
    def genfunc(a, b, c):
        return 'default'

    with pytest.raises(ValueError) as exc_info:
        genfunc(1, 2, 3, 4)
    assert 'Received too many positional arguments.' in str(exc_info)

    with pytest.raises(ValueError) as exc_info:
        genfunc(1, 2, d=3)
    assert 'One or more keyword arguments don\'t exist in the generic function.' in str(exc_info)
