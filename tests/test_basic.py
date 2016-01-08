import pytest
import polyfuncs


def test_genfunc_with_only_default_impl():
    @polyfuncs.generic
    def genfunc(n):
        return n * 2
    assert genfunc(4) == 8


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

