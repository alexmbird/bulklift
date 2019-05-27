""" Utility functions to sanitize filenames """

import string
from pathlib import Path


def dummy_sanitize(path, replace=''):
  """ A no-op sanitizer to use for defaults """
  return Path(path)


# INVALID_VFAT_CHARS = '?<>\\:*|"'
VALID_VFAT_CHARS = string.ascii_letters + string.digits + '._+-()[]& '

def vfat_sanitize(path, replace=''):
  """ Return a version of `path` sanitized for fat32/vfat filesystems by
      removing disallowed characters.  '/' is not valid in fat32 filenames but
      we permit it as a dir specifier.   """
  path = Path(path)
  def sanitize(s):
    return ''.join([c if c in VALID_VFAT_CHARS else replace for c in str(s)])
  if path.is_absolute():
    return Path(path.root, *map(sanitize, path.parts[1:]))
  else:
    return Path(*map(sanitize, path.parts))


# Publish a map of sanitizers for easy access
FILENAME_SANITIZERS = {
  None: dummy_sanitize,
  False: dummy_sanitize,
  'none': dummy_sanitize,
  'vfat': vfat_sanitize
}
