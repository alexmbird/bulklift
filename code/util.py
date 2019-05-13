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


def dict_not_nulls(d, unwanted=(None, {}, [])):
  """ Return a new dict containing pairs from the original where the value is
      not empty  """
  new = {}
  for k, v in d.items():
    if isinstance(v, dict):
      v = dict_not_nulls(v)
    if v not in unwanted:
      new[k] = v
  return new


def available_cpu_count():
  """ Return a sensible estimate for the max. number of cores available """
  try:
    return len(os.sched_getaffinity(0))
  except AttributeError:
    return os.cpu_count()
