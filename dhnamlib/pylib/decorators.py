
import functools
import inspect

from . import filesys


# def cache(func):
#     """keep a cache of previous function calls.
#     it's similar to functools.lru_cache"""

#     cache_memory = {}

#     @functools.wraps(func)
#     def cached_func(*args, **kwargs):
#         cache_key = args + tuple(kwargs.items())
#         if cache_key not in cache_memory:
#             cache_memory[cache_key] = func(*args, **kwargs)
#         return cache_memory[cache_key]

#     cached_func.cache = cache_memory

#     return cached_func


def cache(func):
    return functools.lru_cache(maxsize=None)(func)


def cached_property(func):
    return property(cache(func))


# def singleton(func):
#     @functools.wraps(func)
#     def decorated_func(*args, **kwargs):
#         if decorated_func.singleton is None:
#             decorated_func.singleton = func(*args, **kwargs)
#         else:
#             raise Exception('This function is already evaluated.')
#         return decorated_func.singleton

#     decorated_func.singleton = None

#     return decorated_func


def unnecessary(func):
    called = False

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        nonlocal called
        if not called:
            called = True
            print("Unneccessary function {} is called.".format(func.__name__))
        return func(*args, **kwargs)

    return new_func


def abstractfunction(func):
    @functools.wraps(func)
    def new_func(*args, **kwargs):
        raise NotImplementedError(
            "The abstract function '{}' is not implemented".format(func.__name__))
    return new_func



# def load_after_save(file_path_arg_name, *, load_func, save_func):
#     import os

#     def load_after_save_decorator(func):
#         @functools.wraps(func)
#         def load_after_save_func(*args, **kwargs):
#             file_path = kwargs[file_path_arg_name]
#             del kwargs[file_path_arg_name]
#             if not os.path.isfile(file_path):
#                 save_func(file_path, func(*args, **kwargs))
#             return load_func(file_path)

#         return load_after_save_func

#     return load_after_save_decorator


save_load_pair_dict = dict(
    pickle=(filesys.pickle_save, filesys.pickle_load),
    json=(filesys.json_save, filesys.json_load),
    json_pretty=(filesys.json_pretty_save, filesys.json_load),
    extended_json=(filesys.extended_json_save, filesys.extended_json_load),
    extended_json_pretty=(filesys.extended_json_pretty_save, filesys.extended_json_load),
)


def file_cache(file_path_arg_name='file_cache_path', *, save_fn=None, load_fn=None, format='pickle'):
    '''
    Example 1
    >>> from dhnamlib.pylib.filesys import json_save, json_load
    >>> from dhnamlib.pylib.decorators import file_cache
    >>>
    >>> @file_cache('cache_path', save_fn=json_save, load_fn=json_load)
    >>> def make_dict_and_print(*pairs):
    >>>     d = dict(pairs)
    >>>     print('make_dict_and_print is called')
    >>>     return d
    >>>
    >>> pairs = [['a', 2], ['b', 4], ['c', 6]]
    >>> d1 = make_dict_and_print(*pairs, cache_path='./path/to/cache.json')
    >>> d2 = make_dict_and_print(*pairs, cache_path='./path/to/cache.json')
    >>> print(d1 == d2)

    Example 2
    >>> @file_cache(format='json')
    >>> def make_dict_and_print(*pairs):
    >>>     d = dict(pairs)
    >>>     print('make_dict_and_print is called')
    >>>     return d
    '''
    import os

    if format is not None:
        assert save_fn is load_fn is None
        save_fn, load_fn = save_load_pair_dict[format]

    def file_cache_decorator(func):
        @functools.wraps(func)
        def file_cache_func(*args, **kwargs):
            file_path = kwargs.get(file_path_arg_name)
            assert file_path is not None, f'\'{file_path_arg_name}\' is not designated'
            del kwargs[file_path_arg_name]

            if os.path.isfile(file_path):
                obj = load_fn(file_path)
            else:
                obj = func(*args, **kwargs)
                filesys.mkdirs_unless_exist(file_path)
                save_fn(obj, file_path)
            return obj

        return file_cache_func

    return file_cache_decorator


fcache = file_cache(format='extended_json_pretty')


def curry(func):
    '''
    Example
    >>> @curry
    >>> def func(a, b, c, *, d, e, f=6, g=7):
    >>>     return (a, b, c, d, e, f, g)
    >>>
    >>> print(func(1, 2)(3, 4, 5))
    >>> print(func(1, 2, 3, 4, 5))
    >>> print(func(1, 2, d=4)(3, e=5))
    >>> print(func(1, 2, d=4)(3, e=5, f=66))
    '''

    signature = inspect.signature(func)
    param_keys = []
    optional_param_keys = set()
    reading_optional_param = False
    for name, param in signature.parameters.items():
        param_str = str(param)
        if "=" in param_str:  # e.g. var='default-value' -> not allowed
            reading_optional_param = True
            optional_param_keys.add(name)
        else:
            assert param_str == '*' or not param_str.startswith('*')  # e.g. *args or **kwargs -> not allowed
            assert not reading_optional_param
            param_keys.append(name)

    placeholder = object()
    param_dict = dict([k, placeholder] for k in param_keys)

    def make_curried(_param_dict, positional_arg_count):
        def curried(*args, **kwargs):
            param_dict = dict(_param_dict)
            for idx, arg in enumerate(args, positional_arg_count):
                assert param_dict[param_keys[idx]] is placeholder
                param_dict[param_keys[idx]] = arg

            for k, v in kwargs.items():
                if k in optional_param_keys:
                    assert k not in param_dict
                else:
                    assert k in param_dict
                    assert param_dict[k] is placeholder
                param_dict[k] = v

            if all(value is not placeholder for value in param_dict.values()):
                return func(**param_dict)
            else:
                return make_curried(param_dict, positional_arg_count + len(args))
        return curried

    return make_curried(param_dict, 0)


class Register:
    '''
    Example
    >>> register = Register(strategy='lazy')
    >>> name_fn = register.retrieve('name-fn')
    >>>
    >>> @register('name-fn')
    >>> def full_name(first, last):
    >>>     return ' '.join([first, last])
    >>>
    >>> print(name_fn('John', 'Smith'))
    '''

    strategies = ['instant', 'lazy', 'conditional']

    def __init__(self, strategy='instant'):
        assert strategy in self.strategies
        self.strategy = strategy
        self.memory = dict()

    @curry
    def __call__(self, identifier, obj):
        assert identifier not in self.memory
        self.memory[identifier] = obj
        return obj

    # def __call__(self, identifier, func=None):
    #     if func is None:
    #         def decorator(func):
    #             assert identifier not in self.memory
    #             self.memory[identifier] = func
    #             return func
    #         return decorator
    #     else:
    #         assert identifier not in self.memory
    #         self.memory[identifier] = func

    def retrieve(self, identifier, strategy=None):
        if strategy is None:
            strategy = self.strategy
        else:
            assert strategy in self.strategies

        if (strategy == 'lazy') or (strategy == 'conditional' and identifier not in self.memory):
            registered = LazyValue(self, identifier)
        else:
            assert strategy in ['instant', 'conditional']
            registered = self.memory[identifier]

        return registered

    @staticmethod
    def _msg_not_registered(identifier):
        return f'"{identifier}" is not registered.'


class LazyValue:
    def __init__(self, register, identifier):
        self.register = register
        self.identifier = identifier

    def get(self):
        if self.identifier in self.register.memory:
            return self.register.memory[self.identifier]
        else:
            raise Exception(Register._msg_not_registered(self.identifier))

    def __call__(self, *args, **kwargs):
        if self.identifier in self.register.memory:
            return self.register.memory[self.identifier](*args, **kwargs)
        else:
            raise Exception(Register._msg_not_registered(self.identifier))
