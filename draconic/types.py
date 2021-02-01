import operator as op
from collections import UserList, UserString

from .exceptions import *

__all__ = (
    'safe_list', 'safe_dict', 'safe_set', 'safe_str', 'approx_len_of'
)


# ---- size helper ----
def approx_len_of(obj, visited=None):
    """Gets the approximate size of an object (including recursive objects)."""
    if isinstance(obj, (str, bytes, UserString)):
        return len(obj)

    if hasattr(obj, "__approx_len__"):
        return obj.__approx_len__

    if visited is None:
        visited = [obj]

    size = op.length_hint(obj)

    if isinstance(obj, dict):
        obj = obj.items()

    try:
        for child in iter(obj):
            if child in visited:
                continue
            size += approx_len_of(child, visited)
            visited.append(child)
    except TypeError:  # object is not iterable
        pass

    try:
        setattr(obj, "__approx_len__", size)
    except AttributeError:
        pass

    return size


# ---- types ----
# each function is a function that returns a class based on Draconic config
# ... look, it works
def safe_list(config):
    class SafeList(UserList):  # extends UserList so that [x] * y returns a SafeList, not a list
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.__approx_len__ = approx_len_of(self)

        def append(self, obj):
            if approx_len_of(self) + 1 > config.max_const_len:
                _raise_in_context(IterableTooLong, "This list is too long")
            super().append(obj)
            self.__approx_len__ += 1

        def extend(self, iterable):
            other_len = approx_len_of(iterable)
            if approx_len_of(self) + other_len > config.max_const_len:
                _raise_in_context(IterableTooLong, "This list is too long")
            super().extend(iterable)
            self.__approx_len__ += other_len

        def pop(self, i=-1):
            retval = super().pop(i)
            self.__approx_len__ -= 1
            return retval

        def remove(self, item):
            super().remove(item)
            self.__approx_len__ -= 1

        def clear(self):
            super().clear()
            self.__approx_len__ = 0

        def __mul__(self, n):
            # to prevent the recalculation of the length on list mult we manually set a new instance's
            # data and approx len (JIRA-54)
            new = SafeList()
            new.data = self.data * n
            new.__approx_len__ = self.__approx_len__ * n
            return new

    return SafeList


def safe_set(config):
    class SafeSet(set):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.__approx_len__ = approx_len_of(self)

        def update(self, *s):
            other_lens = sum(approx_len_of(other) for other in s)
            if approx_len_of(self) + other_lens > config.max_const_len:
                _raise_in_context(IterableTooLong, "This set is too large")
            super().update(*s)
            self.__approx_len__ += other_lens

        def add(self, element):
            if approx_len_of(self) + 1 > config.max_const_len:
                _raise_in_context(IterableTooLong, "This set is too large")
            super().add(element)
            self.__approx_len__ += 1

        def union(self, *s):
            if approx_len_of(self) + sum(approx_len_of(other) for other in s) > config.max_const_len:
                _raise_in_context(IterableTooLong, "This set is too large")
            return SafeSet(super().union(*s))

        def pop(self):
            retval = super().pop()
            self.__approx_len__ -= 1
            return retval

        def remove(self, element):
            super().remove(element)
            self.__approx_len__ -= 1

        def discard(self, element):
            super().discard(element)
            self.__approx_len__ -= 1

        def clear(self):
            super().clear()
            self.__approx_len__ = 0

    return SafeSet


def safe_dict(config):
    class SafeDict(dict):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.__approx_len__ = approx_len_of(self)

        def update(self, other_dict=None, **kvs):
            if other_dict is None:
                other_dict = {}

            other_lens = approx_len_of(other_dict) + approx_len_of(kvs)
            if approx_len_of(self) + other_lens > config.max_const_len:
                _raise_in_context(IterableTooLong, "This dict is too large")

            super().update(other_dict, **kvs)
            self.__approx_len__ += other_lens

        def __setitem__(self, key, value):
            other_len = approx_len_of(value)
            if approx_len_of(self) + other_len > config.max_const_len:
                _raise_in_context(IterableTooLong, "This dict is too large")
            self.__approx_len__ += other_len
            return super().__setitem__(key, value)

        def pop(self, k):
            retval = super().pop(k)
            self.__approx_len__ -= 1
            return retval

        def __delitem__(self, key):
            super().__delitem__(key)
            self.__approx_len__ -= 1

    return SafeDict


def safe_str(config):
    # noinspection PyShadowingBuiltins, PyPep8Naming
    # naming it SafeStr would break typeof backward compatibility :(
    class str(UserString):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def center(self, width, *args):
            if width > config.max_const_len:
                _raise_in_context(IterableTooLong, "This str is too large")
            return super().center(width, *args)

        def encode(self, *_, **__):
            _raise_in_context(FeatureNotAvailable, "This method is not allowed")

        def expandtabs(self, tabsize=8):
            if self.count('\t') * tabsize > config.max_const_len:
                _raise_in_context(IterableTooLong, "This str is too large")
            return super().expandtabs(tabsize)

        def format(self, *args, **kwargs):
            _raise_in_context(FeatureNotAvailable, "This method is not allowed")

        def format_map(self, mapping):
            _raise_in_context(FeatureNotAvailable, "This method is not allowed")

        def join(self, seq):
            i = list(seq)
            if len(i) * len(self) + approx_len_of(i) > config.max_const_len:
                _raise_in_context(IterableTooLong, "This str is too large")
            return super().join(i)

        def ljust(self, width, *args):
            if width > config.max_const_len:
                _raise_in_context(IterableTooLong, "This str is too large")
            return super().ljust(width, *args)

        def replace(self, old, new, maxsplit=-1):
            if maxsplit > 0:
                n = maxsplit
            else:
                n = self.count(old)
            if n * (len(new) - len(old)) + len(self) > config.max_const_len:
                _raise_in_context(IterableTooLong, "This str is too large")
            return super().replace(old, new, maxsplit)

        def rjust(self, width, *args):
            if width > config.max_const_len:
                _raise_in_context(IterableTooLong, "This str is too large")
            return super().rjust(width, *args)

        def translate(self, table):
            # this is kind of a disgusting way to check the worst-case length
            # and is an overestimate by a multiplicative factor of len(table)
            # but it is certainly an overestimate
            if approx_len_of(table) * len(self) > config.max_const_len:
                _raise_in_context(IterableTooLong, "This str is too large")
            return super().translate(table)

        def zfill(self, width):
            if width > config.max_const_len:
                _raise_in_context(IterableTooLong, "This str is too large")
            return super().zfill(width)

    return str
