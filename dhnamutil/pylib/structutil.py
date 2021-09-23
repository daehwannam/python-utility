
import re

from .typeutil import isanyinstance


class AttrDict(dict):
    # https://stackoverflow.com/a/14620633
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def rename_attr(self, old_name, new_name):
        assert new_name not in self
        self[new_name] = self[old_name]
        del self[old_name]

    # def get_attr_gen(self, *attr_keys):
    #     # if len(attr_keys) == 0:
    #     #     return ()
    #     if len(attr_keys) == 1:
    #         if isinstance(attr_keys[0], str):
    #             attr_keys = attr_keys[0].replace(',', '').split()
    #         else:
    #             attr_keys = attr_keys[0]  # attr_keys[0] is a sequence such as list or tuple
    #     for attr in attr_keys:
    #         yield self[attr]


# def get_recursive_attr_dict(obj):
#     if isinstance(obj, AttrDict):
#         return obj
#     elif isinstance(obj, dict):
#         return AttrDict(
#             (k, get_recursive_attr_dict(v))
#             for k, v in obj.items())
#     elif any(isinstance(obj, typ) for typ in [list, tuple, set]):
#         return type(obj)(get_recursive_attr_dict(elem) for elem in obj)
#     else:
#         return obj


def get_recursive_dict(obj, dict_cls=dict):
    if issubclass(type(dict_cls), type) and isinstance(obj, dict_cls):
        return obj
    elif isinstance(obj, dict):
        return dict_cls(
            (k, get_recursive_dict(v, dict_cls))
            for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set)):
        return type(obj)(get_recursive_dict(elem, dict_cls) for elem in obj)
    else:
        return obj


def copy_recursively(obj):
    if isanyinstance(obj, [list, tuple, set]):
        return type(obj)(map(copy_recursively, obj))
    elif isinstance(obj, dict):
        return type(obj)([copy_recursively(k), copy_recursively(v)]
                         for k, v in obj.items())
    else:
        return obj


class TreeStructure:
    @classmethod
    def create_root(cls, value, terminal=False):
        struct = cls(value, terminal, None)
        struct.opened = not terminal
        return struct

    def __init__(self, value, terminal, prev):
        self.value = value
        self.terminal = terminal
        self.prev = prev

    def __repr__(self):
        lisp_style = True
        enable_prev = True

        num_reduces = 0
        tree = self
        while not tree.is_closed_root():
            num_reduces += 1
            tree = tree.reduce()

        representation = self.repr_opened(
            lisp_style=lisp_style, enable_prev=enable_prev)

        # 'representation' may have a trailing whitespace char, so '.strip' is used
        return representation.strip() + "}" * num_reduces

    def repr_opened(self, lisp_style, enable_prev, symbol_repr=False):
        representation = str(self.value)  # or repr_opened(self.value)
        if symbol_repr:
            representation = camel_to_symbol(representation)
        if not self.terminal:
            representation = '(' + representation + ' ' if lisp_style else \
                             representation + '('
            if not self.opened:
                delimiter = ' ' if lisp_style else ', '
                representation = representation + \
                    delimiter.join(child.repr_opened(lisp_style=lisp_style, enable_prev=False)
                                   for child in self.children) + ')'
        if self.prev and enable_prev:
            if self.prev.is_closed():
                delimiter = ' ' if lisp_style else ', '
                representation = '{}{}{}'. format(
                    self.prev.repr_opened(lisp_style=lisp_style, enable_prev=True),
                    delimiter, representation)
            else:
                representation = '{}{}'. format(
                    self.prev.repr_opened(lisp_style=lisp_style, enable_prev=True),
                    representation)

        return representation

    def is_opened(self):
        return not self.terminal and self.opened

    def is_closed(self):
        return self.terminal or not self.opened

    def push_term(self, value):
        return self.__class__(value, True, self)

    def push_nonterm(self, value):
        tree = self.__class__(value, False, self)
        tree.opened = True
        return tree

    def reduce(self, value=None):
        opened_tree, children = self.get_opened_tree_children()
        return opened_tree.reduce_with_children(children, value)

    def reduce_with_children(self, children, value=None):
        if value is None:
            value = self.value

        new_tree = self.__class__(value, False, self.prev)
        new_tree.opened = False
        new_tree.children = children

        return new_tree

    def get_parent_siblings(self):
        tree = self.prev  # starts from prev
        reversed_siblings = []
        while tree.is_closed():
            reversed_siblings.append(tree)
            tree = tree.prev
        return tree, tuple(reversed(reversed_siblings))

    def get_opened_tree_children(self):
        tree = self  # starts from self
        reversed_children = []
        while tree.is_closed():
            reversed_children.append(tree)
            tree = tree.prev
        return tree, tuple(reversed(reversed_children))

    def is_root(self):
        return self.prev is None

    def is_closed_root(self):
        return self.is_closed() and self.is_root()

    def is_complete(self):  # == is_closed_root
        return self.is_root() and self.is_closed()

    def get_values(self):
        values = []
        self._construct_values(values)
        return values  # values don't include it's parent

    def _construct_values(self, values):
        values.append(self.value)
        if not self.terminal:
            for child in self.children:
                child._construct_values(values)

    def get_all_values(self):
        def get_values(tree):
            if tree.is_closed():
                return tree.get_values()
            else:
                return [tree.value]

        all_values = []

        def recurse(tree):
            if not tree.is_root():
                parent, siblings = tree.get_parent_siblings()
                recurse(parent)
                for sibling in siblings:
                    all_values.extend(get_values(sibling))
            all_values.extend(get_values(tree))

        recurse(self)
        return all_values

    def count_nodes(self, enable_prev=True):
        count = 1
        if enable_prev and self.prev:
            count += self.prev.count_nodes()
        if not self.terminal and not self.opened:
            for child in self.children:
                count += child.count_nodes(False)
        return count

    def get_last_value(self):
        if self.terminal or self.opened:
            return self.value
        else:
            return self.children[-1].get_last_value()

    def find_sub_tree(self, item, key=lambda x: x.value):
        # don't consider 'prev'
        if key(self) == item:
            return self
        elif self.terminal:
            return None
        else:
            for child in self.children:
                sub_tree = child.find_sub_tree(item, key)
                if sub_tree:
                    return sub_tree
            else:
                return None


first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def camel_to_symbol(name):
    s1 = first_cap_re.sub(r'\1-\2', name)
    return all_cap_re.sub(r'\1-\2', s1).lower()


def camel_to_snake(name):
    s1 = first_cap_re.sub(r'\1-\2', name)
    return all_cap_re.sub(r'\1-\2', s1).lower()


class abidict(dict):
    'Asymmetry bidirectional dictionary'

    def __init__(self, *args, **kwargs):
        super(abidict, self).__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value, set()).add(key)

    def __setitem__(self, key, value):
        if key in self:
            self._del_inverse_item(key)
        super(abidict, self).__setitem__(key, value)
        self.inverse.setdefault(value, set()).add(key)

    def __delitem__(self, key):
        self._del_inverse_item(key)
        super(abidict, self).__delitem__(key)

    def _del_inverse_item(self, key):
        value = self[key]
        self.inverse[value].remove(key)
        if not self.inverse[value]:
            del self.inverse[value]


sep_pattern = re.compile('[ ,]+')


def namedlist(typename, field_names):
    if not isinstance(field_names, (list, tuple)):
        field_names = sep_pattern.split(field_names)
    name_to_idx_dict = dict(map(reversed, enumerate(field_names)))

    class NamedList(list):
        def __init__(self, *args, **kwargs):
            assert (len(args) + len(kwargs)) == len(field_names)
            super(NamedList, self).__init__([None] * len(field_names))
            for idx in range(len(args)):
                self[idx] = args[idx]
            for k, v in kwargs.items():
                self[name_to_idx_dict[k]] = v

        def __getattr__(self, key):
            if key in name_to_idx_dict:
                return self[name_to_idx_dict[key]]
            else:
                return super(NamedList, self).__getattr__(key)

        def __setattr__(self, key, value):
            if key in name_to_idx_dict:
                self[name_to_idx_dict[key]] = value
            else:
                # super(NamedList, self).__setattr__(key, value)
                raise AttributeError("'NamedList' object doesn't allow new attributes.")

        def __repr__(self):
            return ''.join(
                [f'{typename}',
                 '(',
                 ', '.join(f'{name}={self[name_to_idx_dict[name]]}' for name in field_names),
                 ')'])

        def append(self, *args, **kwargs):
            raise Exception('This method is not used')

        def extend(self, *args, **kwargs):
            raise Exception('This method is not used')

        @classmethod
        def get_attr_idx(cls, attr):
            return name_to_idx_dict[attr]

    NamedList.__name__ = typename
    NamedList.__qualname__ = typename
    return NamedList

    # A(x=1, y=2, z=3)


def test_namedlist():
    A = namedlist('A', 'x,    y    z')
    a = A(1, z=3, y=2)
    print(a.x)
    a.x = 10
    print(a[0])
    print(A)
    print(a)
