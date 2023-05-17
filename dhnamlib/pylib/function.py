
import functools

# it can be replaced with cache decorator

# def make_get_singleton(name, func):
#     def get_singleton():
#         if name not in singleton_dict:
#             singleton_dict[name] = func()
#         return singleton_dict[name]
#     return get_singleton


# singleton_dict = {}

def identity(x):
    return x


def loop(fn, coll):
    for elem in coll:
        fn(elem)


def starloop(fn, coll):
    for elem in coll:
        fn(*elem)


def starmap(fn, coll):
    for elem in coll:
        yield fn(*elem)


def compose(*functions):
    '''
    >>> def f(x):
    ...     return x + 10
    >>>
    >>> def g(x):
    ...     return x * 10
    >>>
    >>> def h(x):
    ...     return x - 10
    >>>
    >>> f(g(h(5)))
    -40
    >>> compose(f, g, h)(5)
    -40
    '''
    # https://stackoverflow.com/a/16739663
    first_function, *rest_functions = reversed(functions)

    def apply(input, func):
        return func(input)

    def composed(*args, **kwargs):
        return functools.reduce(apply, rest_functions, first_function(*args, **kwargs))

    return composed
