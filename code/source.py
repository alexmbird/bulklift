import os.path
from pathlib import Path
import shutil

from clint.textui import indent, puts, colored

from manifest import Manifest
from transcoders import TRANSCODERS


class MediaSourceDir(object):
  """ A single directory within the media source tree.  The existence of a dir
      doesn't necessarily imply it has transcodable content - that requires a
      valid manifest file with one or more targets enabled.  """

  def __init__(self, path, parent):
    self.parent = parent
    self.path = Path(path).resolve()  # resolve() is important - keep it!
    self.manifest = Manifest.load(path)


  def walk(self):
    """ Recursively walk our tree, yielding a MediaSourceDir for every
        subdirectory we find.  """
    for p in self.path.iterdir():
      if p.is_dir() and not p.name.startswith('.'):
        yield from MediaSourceDir(p, self).walk()
    if self.manifest.exists():  # only dirs with a manifest, not their subdirs
      yield self


  def targets(self, output=None):
    """ Yield transcoder jobs for this directory and its children  """
    for msd in self.walk():
      for name, spec in msd.manifest.outputs_enabled:
        if name == output:
          klass = TRANSCODERS[spec['codec']]
          yield klass(
            msd, msd.manifest['metadata'], name, spec, msd.manifest['config']
          )


  def outputAlbumPaths(self, output=None):
    """ Convenience method: list all album paths this source tree can be
        expected to generate """
    for msd in self.walk():
      for target in msd.targets(output):
        yield target.output_album_path


  def __str__(self):
    return "<{} {}>".format(self.__class__.__name__, self.path)


class MediaSourceRoot(MediaSourceDir):
  """ A special kind of MediaSourceDir that is the root of the tree.  Contains
      extra methods that only make sense when called over a complete tree. """

  def __init__(self, path):
    """ Variant of the constructor without a parent arg, because root has no
        parents.  """
    super(MediaSourceRoot,self).__init__(path, None)


  def cleanup(self, output=None):
    """ Remove any deprecated directories from the output tree, i.e. those that
        were generated from a manifest/target that no longer exists """
    expected_dirs = [str(p) for p in self.outputAlbumPaths(output)]
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
    for path in self.outputRootPaths(output):
      _clean(path)


  def outputRootPaths(self):
    """ Convenience: return all target tree roots covered by this MSD, enabled
        or not.  """
    return [
      Path(os.path.expandvars(spec['path']))
      for name, spec in self.manifest.outputs
    ]
