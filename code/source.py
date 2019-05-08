from pathlib import Path

from clint.textui import indent, puts

from manifest import Manifest
from transcoders import TRANSCODERS


class MediaSourceDir(object):

  def __init__(self, path, parent):
    self.parent = parent
    self.path = path
    self.manifest = Manifest.load(path)


  def walk(self):
    subnodes = [MediaSourceDir(p, self) for p in self.path.iterdir() if p.is_dir()]
    for node in subnodes:
      node.doTranscoding()
      node.walk()


  def doTranscoding(self):
    for o_name, o_spec in self.manifest.outputs:
      transcoder = TRANSCODERS[o_spec['codec']](
        self, self.manifest.metadata, o_spec, self.manifest.config
      )
      puts(str(transcoder))
      with indent(2):
        transcoder.transcode()


  def __str__(self):
    return "<{} {}>".format(self.__class__.__name__, self.path)
