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


def test_parameter_matching():
    assert polyfuncs._match_arg_values_for_partial_func([10, 20, 30, 40], ['a', 'b', 'c', 'd'], ['a', 'b', 'c', 'd']) == [10, 20, 30, 40]
    assert polyfuncs._match_arg_values_for_partial_func([10, 20, 30, 40], ['a', 'b', 'c', 'd'], ['b', 'c']) == [20, 30]
    assert polyfuncs._match_arg_values_for_partial_func([10, 20, 30, 40], ['a', 'b', 'c', 'd'], ['c', 'b']) == [30, 20]
    assert polyfuncs._match_arg_values_for_partial_func([10, 20, 30, 40], ['a', 'b', 'c', 'd'], ['d', 'a']) == [40, 10]
    assert polyfuncs._match_arg_values_for_partial_func([10, 20, 30, 40], ['a', 'b', 'c', 'd'], ['b']) == [20]
    assert polyfuncs._match_arg_values_for_partial_func([10, 20, 30, 40], ['a', 'b', 'c', 'd'], []) == []
    with pytest.raises(ValueError):
        polyfuncs._match_arg_values_for_partial_func([10, 20, 30, 40], ['a', 'b', 'c', 'd'], ['e'])


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
