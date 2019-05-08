import collections
import os
import os.path
import enum


def dict_deep_merge(a, b):
  """ deep-merge the contents of dict b into dict a """
  for k, v in b.items():
    if (k in a and isinstance(a[k], dict)
          and isinstance(b[k], collections.Mapping)):
        dict_deep_merge(a[k], b[k])
    else:
        a[k] = b[k]


# None is sometimes a legit value so let's use this to prevent clashes
DICT_DEFAULTS = enum.Enum('DictDefaults', 'no_default')

def dict_deep_get(d, path, default=DICT_DEFAULTS.no_default):
  """ Try to extract a value from a tree of dicts.  `path` is a list of keys
      in the order that they will be accessed.  """
  if not isinstance(path, (list, tuple)):  # easy to pass a string by mistake
    raise TypeError("path must be a list or tuple")
  if len(path) == 0:
    return d
  else:
    try:
      return dict_deep_get(d[path[0]], path[1:], default)
    except KeyError:
      if default is not DICT_DEFAULTS.no_default:
        return default
      else:
        raise


# def is_executable(path):
#   return os.path.isfile(path) and os.access(path, os.X_OK)
