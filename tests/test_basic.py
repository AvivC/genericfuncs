import polyfuncs


def test_genfunc_with_only_default_impl():
    @polyfuncs.generic
    def genfunc(n):
        return n * 2
    assert genfunc(4) == 8


def test_genfunc_correct_impl_invoked():
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

