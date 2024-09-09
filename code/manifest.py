import yaml
import functools
from copy import deepcopy
from pathlib import Path
import pprint

from clint.textui import puts, colored

from util.data import dict_deep_merge, available_cpu_count
from util.file import is_audio_dir, expandvars


class ManifestError(Exception):
  "Problem reading or parsing a manifest file"


class MetadataError(ManifestError):
  "A required piece of metadata was missing"


class ManifestConfig(dict):
  """ Dict-like representing core config, with sensible defaults """

  # Suitable for most things by an artist; override for mixes & soundtracks
  DFL_ALBUM_DIR_TEMPLATE = "{genre}/{artist}/{year} {album}"

  def __init__(self, *args, **kwargs):
    super(ManifestConfig, self).__init__(*args, **kwargs)
    self.setdefault('transcoding', {})  # see _getBinary()
    tc = self['transcoding']
    tc.setdefault('ffmpeg_path', None)
    tc['ffmpeg_path'] = expandvars(tc['ffmpeg_path'])
    tc.setdefault('threads', available_cpu_count())
    tc.setdefault('rewrite_metadata', {})
    tc['rewrite_metadata'].setdefault('comment', '')
    self.setdefault('r128gain', {})
    rg = self['r128gain']
    rg.setdefault('r128gain_path', None)
    rg['r128gain_path'] = expandvars(rg['r128gain_path'])
    rg.setdefault('ffmpeg_path', None)
    rg['ffmpeg_path'] = expandvars(rg['ffmpeg_path'])
    rg.setdefault('threads', None)
    rg.setdefault('type', 'album')
    self.setdefault('target', {})
    self['target'].setdefault('album_dir', self.DFL_ALBUM_DIR_TEMPLATE)

  def dump(self):
    """Dump human-readable config for debugging"""
    pp = pprint.PrettyPrinter(indent=2)
    puts(pp.pformat(self))


class ManifestOutput(dict):
  """ Dict-like representing an output, with sensible defaults """

  def __init__(self, *args, **kwargs):
    # print("creating a ManifestOutput from: {}".format(args[0]))
    super(ManifestOutput, self).__init__(*args, **kwargs)
    self.setdefault('name', 'unnamed')
    self.setdefault('sanitize_paths', None)
    self.setdefault('formats', []) # accepted formats in order of preference, eg. ['opus', 'mp3']
    self.setdefault('enabled', False)
    self.setdefault('lame_vbr', 3)
    self.setdefault('opus_bitrate', '128k')
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
    self['path'] = expandvars(self['path'])

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

  # Metadata must contain at least these fields
  METADATA_REQUIRED = ('artist', 'album', 'genre', 'year')


  def __init__(self, path, mapping={}, **kwargs):
    """ Create a manifest representing `path`.  Other args as for dict. """
    super(Manifest, self).__init__(mapping, **kwargs)
    self.path = path

    # A couple of sanity checks
    if not isinstance(self.get('outputs', []), list):
      raise MetadataError(
        "Invalid 'outputs' section for {} - outdated config format?".format(
          self.path
        )
      )

    # Set defaults & translate some of our contents into specialized objects
    self.setdefault('metadata', {})
    self['config'] = ManifestConfig(self.get('config', {}))
    self['outputs'] = [ManifestOutput(oconf) for oconf in self.get('outputs', []) if not oconf.get('deactivate', False)]

  @classmethod
  def manifestFilePath(cls, path):
    return path / cls.MANIFEST_FILE_NAME

  def exists(self):
    """ Return True if this manifest exists on disk """
    return self.manifestFilePath(self.path).is_file()

  @classmethod
  @functools.lru_cache(maxsize=None)
  def loadYaml(cls, dir_path):
    """ Load a yaml-formatted manifest from disk for Path `dir_path` """
    man_path = cls.manifestFilePath(dir_path)
    # puts("Loading {}".format(man_path))
    try:
      with man_path.open('r') as stream:
        data = yaml.safe_load(stream)
    except FileNotFoundError:
      data = {}
    except yaml.scanner.ScannerError as e:
      raise ManifestError("Error parsing {}:\n\n{}".format(man_path, e))
    data.setdefault('root', False)
    return data

  @classmethod
  def fromDir(cls, path, override={}, debug=False):
    """ Load the manifest from `path`, if present, and merge it with any parent
        manifests up to the root """
    if debug:
      puts("Reading manifest from {}".format(path))
    data = deepcopy(cls.loadYaml(path))
    got_root = data.get('root', False)
    # dict_deep_merge() doesn't do lists, so we have to re-pack the outputs
    outputs_data = {o['name']: o for o in data.get('outputs', [])}
    outputs_override = {o['name']: o for o in override.pop('outputs', [])}
    dict_deep_merge(outputs_data, outputs_override)
    data['outputs'] = list(outputs_data.values())
    dict_deep_merge(data, override)
    if got_root:   # must have merged in the root manifest
      return Manifest(path, data)
    if path == path.parent:       # Reached / without finding a root manifest
      raise ManifestError(
        "Root manifest could not be found; did you miss a 'root: true'?"
      )
    return cls.fromDir(path.parent, data, debug=debug)

  def dumpTemplate(self):
    """ Try to infer the directory level we're on and produce an appropriate
        yaml template for the user to edit """
    if self['root']:
      d = dict(self)
    elif is_audio_dir(self.path):
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
    d.setdefault('outputs', [])
    for output in self.outputs:
      wanted = ['name']
      if 'opus' in output['formats']:
        wanted += ['opus_bitrate']
      if 'mp3' in output['formats']:
        wanted += ['lame_vbr']
      new_output = {k:v for k,v in output.items() if k in wanted}
      new_output.setdefault('enabled', True)
      d['outputs'].append(new_output)
    return d

  @property
  def outputs(self):
    """ Return a list of output specs, whether or not they are disabled """
    return self['outputs']

  @property
  def outputs_enabled(self):
    """ Return a list of output specs, but only the ones that are enabled """
    return [o for o in self.outputs if o['enabled']]
