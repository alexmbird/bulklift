import yaml
from copy import deepcopy
from pathlib import Path

from util import dict_deep_merge



class Manifest(dict):
  """ A dict-like object for loading, processing and testing Bulklift
      manifests """

  MANIFEST_FILE_NAME = '.bulklift.yaml'

  # 1 manifest, 1 object
  MANIFEST_CACHE = {}

  # Metadata must contain at least these fields
  METADATA_REQUIRED = ('artist', 'album', 'genre', 'year')


  def __init__(self, path, mapping={}, **kwargs):
    """ Create a manifest representing `path`.  Other args as for dict. """
    if not isinstance(path, Path):
      raise TypeError("Manifest takes pathlib.Path")
    if not path.is_dir():
      raise ValueError("__init__() takes reference to dir, not manifest file")

    super(Manifest, self).__init__(mapping, **kwargs)
    self.path = path


  @classmethod
  def load(cls, path):
    if not isinstance(path, Path):
      raise TypeError("Manifest takes pathlib.Path")
    if not path.is_dir():
      raise ValueError("__init__() takes reference to dir, not manifest file")
    # print("Loading manifest from {}".format(path))
    try:
      return cls.MANIFEST_CACHE[path]
    except KeyError:
      try:
        with open(path / cls.MANIFEST_FILE_NAME, 'r') as stream:
          data = yaml.safe_load(stream)
      except FileNotFoundError:
        data = {}
      if data.get('root', False):
        manifest = Manifest(path, data)
      else:
        if path == path.parent:   # Reached / without finding a root manifest
          raise RecursionError("Root manifest could not be found; did you miss a 'root: true'?")
        parent_manifest = cls.load(path.parent)
        new = deepcopy(parent_manifest)
        dict_deep_merge(new, data)
        new.pop('root', None)  # it is definitely not the root
        manifest = Manifest(path, new)
      cls.MANIFEST_CACHE[path] = manifest
      return manifest


  def is_root(self):
    return self.get('root', False)


  @property
  def config(self):
    return self.get('config', {})


  @property
  def outputs(self):
    return [(name, spec) for name, spec in self.get('outputs', {}).items() if spec.get('enabled', False)]


  @property
  def metadata(self):
    return self.get('metadata', {})


  def is_metadata_complete(self):
    return set(self.METADATA_REQUIRED).issubset(set(self.metadata.keys()))
