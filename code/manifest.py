import yaml
from copy import deepcopy
from pathlib import Path

from clint.textui import puts, colored

from util import dict_deep_merge, available_cpu_count
from transcoders import TRANSCODE_TYPES



class ManifestError(Exception):
  "Problem reading or parsing a manifest file"


class ManifestConfig(dict):
  """ Dict-like representing core config, with sensible defaults """

  # Suitable for most things by an artist; override for mixes & soundtracks
  DFL_ALBUM_DIR_TEMPLATE = "{genre}/{artist}/{year} {album}"

  def __init__(self, *args, **kwargs):
    super(ManifestConfig, self).__init__(*args, **kwargs)
    self.setdefault('transcoding', {})  # see _getBinary()
    self['transcoding'].setdefault('ffmpeg_path', None)
    self['transcoding'].setdefault('threads', available_cpu_count())
    self['transcoding'].setdefault('rewrite_metadata', {})
    self['transcoding']['rewrite_metadata'].setdefault('comment', '')
    self.setdefault('r128gain', {})
    self['r128gain'].setdefault('r128gain_path', None)
    self['r128gain'].setdefault('ffmpeg_path', None)
    self['r128gain'].setdefault('threads', None)
    self.setdefault('target', {})
    self['target'].setdefault('album_dir', self.DFL_ALBUM_DIR_TEMPLATE)


class ManifestOutput(dict):
  """ Dict-like representing an output, with sensible defaults """

  def __init__(self, *args, **kwargs):
    super(ManifestOutput, self).__init__(*args, **kwargs)
    self.setdefault('sanitize_paths', None)
    self.setdefault('codec', 'null')
    self.setdefault('enabled', False)
    self.setdefault('codec_version', None)
    self.setdefault('lame_vbr', 3)
    self.setdefault('opus_bitrate', '128k')
    self.setdefault('gain', {})
    self['gain'].setdefault('album', True)
    self.setdefault('permissions', {})
    self['permissions'].setdefault('dir_mode', None)
    self['permissions'].setdefault('file_mode', None)
    self['permissions'].setdefault('user', None)
    self['permissions'].setdefault('group', None)
    self.setdefault('filters', {})
    self['filters'].setdefault('include', [])
    self['filters'].setdefault('exclude', [])
    if not 'path' in self:
      raise ManifestError("output is missing a 'path' field")


  @property
  def permissions_dir_mode(self):
    """ Return the dir mode configured, if any, in octal """
    dm = self['permissions']['dir_mode']
    return None if dm is None else int(dm, 8)


  @property
  def permissions_file_mode(self):
    """ Return the file mode configured, if any, in octal """
    fm = self['permissions']['file_mode']
    return None if fm is None else int(fm, 8)


class Manifest(dict):
  """ A dict-like object for loading, processing and testing Bulklift
      manifests.  Individual sections may be handled with specialised objects
      that return sensible defaults for fields.  """

  MANIFEST_FILE_NAME = '.bulklift.yaml'

  # 1 manifest, 1 object
  MANIFEST_CACHE = {}

  # Metadata must contain at least these fields
  METADATA_REQUIRED = ('artist', 'album', 'genre', 'year')


  def __init__(self, path, mapping={}, **kwargs):
    """ Create a manifest representing `path`.  Other args as for dict. """
    super(Manifest, self).__init__(mapping, **kwargs)
    self.path = path

    # Set defaults & translate some of our contents into specialized objects
    self['config'] = ManifestConfig(self.get('config', {}))
    self.setdefault('metadata', {})
    self['outputs'] = {
      n: ManifestOutput(s) for n, s in self.get('outputs', {}).items()
    }


  @classmethod
  def manifest_file_name(cls, path):
    return path / cls.MANIFEST_FILE_NAME


  @classmethod
  def load(cls, path):
    """ Load a manifest file, preferring a cached copy if available """
    if not isinstance(path, Path):
      raise TypeError("Manifest takes pathlib.Path")
    if not path.is_dir():
      raise ValueError("__init__() takes reference to dir, not manifest file")
    # print("Loading manifest from {}".format(path))
    try:
      return cls.MANIFEST_CACHE[path]
    except KeyError:
      return cls.loadFresh(path)


  @classmethod
  def loadFresh(cls, path):
    """ Load a manifest file from disk, insert it into the cache and return a
        a fresh Manifest object.  Any previously cached object will be
        replaced.  """
    manifest_path = cls.manifest_file_name(path)
    try:
      with manifest_path.open('r') as stream:
        data = yaml.safe_load(stream)
    except FileNotFoundError:
      data = {}
    except yaml.scanner.ScannerError as e:
      raise ManifestError("Error parsing {}:\n\n{}".format(manifest_path, e))

    data.setdefault('root', False)  # if not root, be explicit about it
    if data['root']:
      manifest = Manifest(path, data)
    else:
      if path == path.parent:   # Reached / without finding a root manifest
        raise RecursionError("Root manifest could not be found; did you miss a 'root: true'?")
      parent_manifest = cls.load(path.parent)
      new = deepcopy(parent_manifest)
      dict_deep_merge(new, data)
      manifest = Manifest(path, new)
    cls.MANIFEST_CACHE[path] = manifest
    return manifest


  def exists(self):
    """ Return True if this manifest exists on disk """
    return self.manifest_file_name(self.path).is_file()


  def is_music_dir(self):
    """ Return True if this path contains any supported media types """
    for p in self.path.iterdir():
      if p.suffix in TRANSCODE_TYPES:
        return True
    return False


  def dumpTemplate(self):
    """ Try to infer the directory level we're on and produce an appropriate
        yaml template for the user to edit """
    if self['root']:
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
    """ Dump yaml suitable to be used as a template for an album manifest.
        FIXME: remove transcoder-specific logic   """
    d = self.genTemplateForArtist()
    m = d.setdefault('metadata', {})
    m.setdefault('album', '')
    m.setdefault('year', '')
    d.setdefault('outputs', {})
    for o_name, o_spec in self['outputs'].items():
      unmasked = ['codec',]
      if o_spec['codec'] == 'opus':
        unmasked += ['opus_bitrate']
      elif o_spec['codec'] == 'lame':
        unmasked += ['lame_vbr']
      d['outputs'][o_name] = {k:v for k,v in o_spec.items() if k in unmasked}
      d['outputs'][o_name].setdefault('enabled', True)  # for new templates default to on
    return d


  @property
  def outputs(self):
    return [(name, spec) for name, spec in self['outputs'].items()]


  @property
  def outputs_enabled(self):
    return [(name, spec) for name, spec in self['outputs'].items() if spec['enabled']]


  def is_metadata_complete(self):
    return set(self.METADATA_REQUIRED).issubset(set(self['metadata'].keys()))
