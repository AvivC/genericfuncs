genericfuncs
============

`genericfuncs` allows you to cleanly implement functions which execute different
implementations depending on the arguments.

This module can be seen as a powerful improvement over Python 3's `singledispatch`:

* Allows dispatch over any boolean callable, not just type checks.
* Allows dispatch over any number of arguments, not just the first argument.

Basic usage::

    # define a generic function
    @genericfuncs.generic
    def func(a):
        # default implementation
        raise TypeError()

    # types can be used as predicates to dispatch on type
    @func.when(int)
    def _when_int(a):
        return a * a

    # any  that returns a boolean can be a predicate
    @func.when(lambda a: a == 'magic')
    def _when_magic_word(a):
        return a.upper()

    # multiple predicates can be used
    @func.when([float, lambda a: a < 0])
    def _when_float_and_negative(a):
        return a * -1

    func(10) --> 100  # _when_int invoked
    func('magic') --> 'MAGIC'  # _when_magic_word invoked
    func(-5.5) --> 5.5  # _when_float_and_negative invoked
    func(Something()) --> TypeError raised  # default implementation invoked

The first predicate that returns True has its mapped implementation invoked.
Predicates are checked in order of definition.

Arguments are injected into predicates and implementations by their name.
This means a predicate or implementation is able to specify only the arguments it needs. For example::

    @generic
    def multiple_params_func(a, b, c):
        return a + b + c  # default implementation

    @multiple_params_func.when(lambda b: b > 10)  # only inject argument `b` to the predicate
    def _when_b_greater_than_10(a):  # only inject `a` to the implementation
        return a * 10

    @multiple_params_func.when(lambda a, b: a % b == 0)  # only inject `a` and `b`
    def _when_a_divisible_by_c(a, b, c):  # use all arguments
        return a / b * c

However the call site must list all mandatory arguments, as usual in Python:::

    multiple_params_func(10, 20, 30) --> 100  # _when_b_great_than_10 invoked
    multiple_params_func(4, 2, 'bla') --> 'blabla'  # _when_a_divisible_by_c invoked
    multiple_params_func(0, 0, 0) --> 0  # default implementation invoked

When defining a predicate, one can list exception types that should not
propagate if raised inside the predicate. For example:::

    @my_generic_func.when(lambda a: a > 10, ignored_errors=[TypeError])
    def _implementation(a):
        ...

When invoking `my_generic_func(MyThing())`, a TypeError will be raised inside the predicate
because MyThing doesn't support `>` operator.
Normally, the error would propagate and probably crash the program.
Specifying `ignored_errors=[TypeError]` makes the error be silently ignored,
moving on to the next predicate.
