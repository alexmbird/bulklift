import yaml
from copy import deepcopy
from pathlib import Path

from util import dict_deep_merge
from transcoders import TRANSCODE_TYPES



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
  def manifest_file_name(cls, path):
    return path / cls.MANIFEST_FILE_NAME


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
        with cls.manifest_file_name(path).open('r') as stream:
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


  def is_music_dir(self):
    """ Return True if this path contains any supported media types """
    for p in self.path.iterdir():
      if p.suffix in TRANSCODE_TYPES:
        return True
    return False


  def dumpTemplate(self):
    """ Try to infer the directory level we're on and produce an appropriate
        yaml template for the user to edit """
    if self.is_root():
      d = dict(self)
    elif self.is_music_dir():
      d = self.genTemplateForAlbum()
    else:
      d = self.genTemplateForArtist()
    return yaml.safe_dump(d)


  def genTemplateForArtist(self):
    """ Dump yaml suitable to be used as a template for an artist manifest """
    d = {k: v for k, v in self.items() if k in ['metadata']}
    m = d.setdefault('metadata', {})
    m.setdefault('genre', '')
    m.setdefault('artist', '')
    return d


  def genTemplateForAlbum(self):
    """ Dump yaml suitable to be used as a template for an album manifest """
    d = self.genTemplateForArtist()
    m = d.setdefault('metadata', {})
    m.setdefault('album', '')
    m.setdefault('year', '')
    unmasked = ['enabled', 'codec', 'lame_vbr', 'opus_bitrate']
    # print("outputs is {}".format(self['outputs']))
    def _clean(spec):
      return {k:v for k,v in spec.items() if k in unmasked}
    d['outputs'] = {o_name: _clean(o_spec) for o_name, o_spec in self['outputs'].items()}
    return d


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
