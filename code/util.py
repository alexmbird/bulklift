import collections
import os
import os.path
from pathlib import Path
import string


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


def filename_matches_globs(path, globs=[]):
  """ Return True if the *filename* at end of `path` matches any of the
      supplied list of glob patterns  """
  f = path.relative_to(path.parent)
  for g in globs:
    if f.match(g):
      return True
  return False


def vfat_sanitize(path):
  """ Return a version of `path` sanitized for fat32/vfat filesystems.  '/' is
      not valid in fat32 filenames but we permit it as a dir specifier.   """
  invalid = '?<>\\:*|"'
  return Path(''.join([v if v not in invalid else '_' for v in str(path)]))
