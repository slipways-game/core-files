# General utilities that didn't fit anywhere else.

#####################################################
# Numeric utilities

def mid(a, b, c):
    if a < b:
        if b < c: return b
        return c if a < c else a
    else:
        if a < c: return a
        return c if b < c else b
def clamp(low, high, value):
    if value < low: return low
    if value > high: return high
    return value
def lerp(a, b, t):
    return a + (b-a) * t
def lerp_clamped(a, b, t):
    return mid(a, b, lerp(a, b, t))
def inverse_lerp(a, b, value):
    return (value - a) / (b - a)
def inverse_lerp_clamped(a, b, value):
    return mid(0.0, 1.0, inverse_lerp(a, b, value))
def mid(a, b, c):
    if a < b:
        if b < c: return b
        return c if a < c else a
    else:
        if a < c: return a
        return c if b < c else b

def max_or(iterable, key = None, default_value = None, as_value_key_tuple = False):
    if key is None: key = lambda x: x
    max_element = default_value
    max_key = key(default_value)
    for x in iterable:
        x_key = key(x)
        if x_key > max_key:
            max_element, max_key = x, x_key
    return (max_element, max_key) if as_value_key_tuple else max_element

def flatten(sequence):
    flattened = []
    for item in sequence:
        if isinstance(item, list):
            flattened += item
        else:
            flattened.append(item)
    return flattened

def permutations(sequence):
    if len(sequence) <= 1: 
        yield sequence
        return
    for index in range(len(sequence)):
        last = sequence[index]
        rest = sequence[:index] + sequence[index+1:]
        for subperm in permutations(rest):
            subperm.append(last)
            yield subperm

def first(iter):
    for elem in iter:
        return elem
    return None

def difficulty_ordinal():
    return clamp(0, 3, game.GameConfig.Difficulty.Ordinal)

class CustomDataAccess:
    """Provides easy access to custom data stored on a model."""
    def __init__(self, host):
        self._host_model = host
        self._cd = self._host_model.CustomData

    def has_value(self, key):
        return self._cd.Has(key)
        
    def set_value(self, key, value):
        self._cd.Set(key, value)

    def get_value(self, key):
        return self._cd.Get(key)

    def get_or(self, key, default_value):
        return self._cd.GetOr(key, default_value)

    def clear_value(self, key):
        return self._cd.Clear(key)

    def __getattr__(self, attr_name):
        return self._cd.Get(attr_name)

    def __setattr__(self, attr_name, value):
        if attr_name[0] != "_":
            self._cd.Set(attr_name, value)
        else:
            self.__dict__[attr_name] = value

class TemporaryDataAccess:
    """Provides the same interface as CustomDataAccess, but just stores the data
    in a temporary dictionary."""
    def __init__(self):
        self._storage = {}

    def has_value(self, key):
        return key in self._storage
        
    def set_value(self, key, value):
        self._storage[key] = value

    def get_value(self, key):
        return self._storage[key]

    def __getattr__(self, attr_name):
        return self._storage[attr_name]

    def __setattr__(self, attr_name, value):
        if attr_name[0] != "_":
            self._storage[attr_name] = value
        else:
            self.__dict__[attr_name] = value
