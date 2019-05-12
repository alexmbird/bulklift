import os.path
from pathlib import Path
import shutil

from clint.textui import indent, puts, colored

from manifest import Manifest
from transcoders import TRANSCODERS


class MediaSourceDir(object):

  def __init__(self, path, parent):
    self.parent = parent
    self.path = Path(path).resolve()  # resolve() is important - keep it!
    self.manifest = Manifest.load(path)


  def walk(self):
    """ Recursively walk our tree, yielding a MediaSourceDir for every
        subdirectory we find.  """
    for p in self.path.iterdir():
      if p.is_dir() and not p.name.startswith('.'):
        yield from self.__class__(p, self).walk()
    yield self


  def targets(self):
    """ Yield transcoder jobs for this directory and its children  """
    for msd in self.walk():
      for name, spec in msd.manifest.outputs_enabled:
        klass = TRANSCODERS[spec['codec']]
        yield klass(
          msd, msd.manifest.metadata, name, spec, msd.manifest.config
        )


  def cleanup(self):
    """ Remove any deprecated directories from the output tree, i.e. those that
        were generated from a manifest/target that no longer exists """
    assert self.manifest.is_root()  # cleanup must have a complete target set
    expected_dirs = [str(p) for p in self.outputAlbumPaths()]
    def isexpected(p):
      return any(map(
        lambda ed: ed.startswith(p), expected_dirs)
      )
    def _clean(victim):
      for entry in victim.iterdir():
        if entry.is_dir():
          _clean(entry)
      if not isexpected(str(victim)):
        puts(colored.red("Removing '{}'".format(victim)))
        shutil.rmtree(str(victim), ignore_errors=True)
    for path in self.outputRootPaths():
      _clean(path)


  def outputRootPaths(self):
    """ Convenience: return all target tree roots covered by this MSD, enabled
        or not.  """
    return [
      Path(os.path.expandvars(spec['path']))
      for name, spec in self.manifest.outputs
    ]


  def outputAlbumPaths(self):
    """ Convenience method: list all album paths this source tree can be
        expected to generate """
    for msd in self.walk():
      for target in msd.targets():
        yield target.output_album_path


  def __str__(self):
    return "<{} {}>".format(self.__class__.__name__, self.path)
