from pathlib import Path

from clint.textui import indent, puts

from manifest import Manifest
from transcoders import TRANSCODERS


class MediaSourceDir(object):

  def __init__(self, path, parent):
    self.parent = parent
    self.path = Path(path).resolve()  # resolve() is important - keep it!
    self.manifest = Manifest.load(path)


  def walk(self):
    """ Recursively walk our tree, yielding every transcoding target we find """
    for p in self.path.iterdir():
      if p.is_dir():
        msd = MediaSourceDir(p, self)
        yield from msd.walk()
    yield from self.targets()


  def targets(self):
    """ Return a list of transcoder jobs specific to this directory """
    def _mktc(name, spec):
      klass = TRANSCODERS[spec['codec']]
      return klass(
        self, self.manifest.metadata, name, spec, self.manifest.config
      )
    return [_mktc(n, s) for n, s in self.manifest.outputs]


  def __str__(self):
    return "<{} {}>".format(self.__class__.__name__, self.path)
