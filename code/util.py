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


# INVALID_VFAT_CHARS = '?<>\\:*|"'
VALID_VFAT_CHARS = string.ascii_letters + string.digits + '._+-/()[]& '

def vfat_sanitize(path, replacement=''):
  """ Return a version of `path` sanitized for fat32/vfat filesystems by
      removing disallowed characters.  '/' is not valid in fat32 filenames but
      we permit it as a dir specifier.   """
  sanitized = ''.join([c if c in VALID_VFAT_CHARS else replacement for c in str(path)])
  return Path(sanitized)
