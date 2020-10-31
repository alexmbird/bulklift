""" Utility functions for handling the filesystem """

from pathlib import Path
import os.path
import functools


##
# File extensions for known formats
##

AUDIO_FORMATS_LOSSY = dict.fromkeys([
  'mp3', 'ogg', 'opus', 'm4a', 'mp4', 'wma'
])

AUDIO_FORMATS_LOSSLESS = dict.fromkeys([
  'flac', 'alac', 'wav', 'ape'
])

AUDIO_FORMATS = dict.fromkeys(
  list(AUDIO_FORMATS_LOSSLESS) + list(AUDIO_FORMATS_LOSSY)
)

IMAGE_FORMATS = dict.fromkeys([
  'jpg', 'jpeg', 'png', 'gif'
])


##
# Utility functions
##

def filename_matches_globs(path, globs=[]):
  """ Return True if the *filename* at end of `path` matches any of the
      supplied list of glob patterns  """
  f = path.relative_to(path.parent)
  # print("filename for matching: {}".format(f))
  for g in globs:
    if f.match(g):
      return True
  return False


def is_audio_dir(path):
  """ Return True if the directory specified by `path` contains music, False
      otherwise """
  for p in path.iterdir():
    if p.is_file():
      if p.suffix.lower().lstrip('.') in AUDIO_FORMATS:
        return True
  return False


@functools.lru_cache(maxsize=2048)
def is_parent_path(parent, child):
  """ Return True if path `child` is within dir `parent`.  Pathlib.Path lacks a
      contains() method so we do it all with strings.  """
  if not parent.is_dir():
    raise ValueError("parent must be a directory")
  return child.resolve().as_posix().startswith(
    parent.resolve().as_posix()
  )


def expandvars(s=None):
  """ Return a copy of string `s` with ${ENV_VAR}s templated in.  If `s` was
      None return None, which is useful for handling config settings.  """
  return os.path.expandvars(s) if s is not None else None
