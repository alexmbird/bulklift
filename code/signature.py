import yaml
from hashlib import sha256

from clint.textui import puts, colored, indent


class Signature(object):
  """ Create & manage Bulklift output signatures.  These cover all files within
      the output dir, including artwork.  Only file *names* are stored, not the
      whole path which is subject to change if the output tree gets moved. """

  SIGNATURE_FILE_NAME = '.bulklift.sig'

  def __init__(self, album_path, mconf, oconf, metadata_rewrites={}):
    """ Initialize signatures fpr path `album_path` """
    self.path = album_path
    self.mconf = mconf
    self.oconf = oconf
    self.metadata_rewrites = metadata_rewrites
    self.tree = {
      'files': {}  # dict of output filename -> data
    }
    try:
      self.load()
      self.dirty = False
    except FileNotFoundError:
      self.dirty = True # no existing signature

  @property
  def signature_file(self):
    return self.path / self.SIGNATURE_FILE_NAME

  def __len__(self):
    """ Return number of known files """
    return len(self.tree['files'])

  def __contains__(self, name):
    """ Return True if filename `name` is mentioned in the signature, False
        otherwise.  """
    return name in self.tree['files']

  def signature(self, source_path, codec):
    """ Return a signature for the file specified by `source_path`.  File can
        be any normal file, not just audio.  `codec` is used to enable the
        inclusion of codec-specific params like lame_vbr; pass None if it isn't
        an audio file.  """
    components = [    # things we always want
      int(source_path.stat().st_mtime),
      '|'.join(["{}:{}" for k, v in self.metadata_rewrites.items()])
    ]
    components.append(self.mconf['r128gain']['type'])
    if codec == 'mp3':
      components.append(self.oconf['lame_vbr'])
    elif codec == 'opus':
      components.append(self.oconf['opus_bitrate'])
    else:
      components.append('')
    sig = '::'.join(map(str, components))
    return sha256(bytes(sig, encoding='utf8')).hexdigest()

  def add(self, name, source_path, codec):
    """ Add signature for the file specified by `name`, taking metadata from
        the original in `source_path`.  Any existing sig for `name` is
        overwritten.  """
    # print("Adding {} to signature".format(name))
    self.tree['files'][name] = self.signature(source_path, codec)
    self.dirty = True

  def has(self, name, source_path, codec):
    """ Return True if the file specified by `path` is present in the signature
        and matches the expected data.  Does not check the filesystem. """
    try:
      return self.tree['files'][name] == self.signature(source_path, codec)
    except KeyError:
      return False

  def is_valid(self, name, source_path, codec):
    """ Return True if the file specified by `name` is present in the
        signature, the source's metadata matches the signature value and the
        expected output actually exists on the filesystem """
    if self.tree['files'].get(name, '') != self.signature(source_path, codec):
      return False
    elif not self.path.joinpath(name).exists():
      return False
    else:
      return True

  def clean(self, verbose=True):
    """ Remove from the signature any files not present in the output dir.
        This can happen after their removal from the source is propagated by
        OutputAlbum's cleanup() method.  """
    expected = dict.fromkeys([p.name for p in self.path.iterdir()])
    if verbose:
      puts("Cleaning orphaned sig entries (sig:{}, dir:{})".format(
        len(self), len(expected))
      )
    with indent(2):
      for name in list(self.tree['files'].keys()):
        if name not in expected:
          del self.tree['files'][name]
          self.dirty = True

  def load(self):
    """ Attempt to load existing signature data """
    with self.signature_file.open('r', encoding='utf8') as stream:
      self.tree = yaml.safe_load(stream)
    self.tree.setdefault('files', {})   # ensure it exists

  def save(self, verbose=True):
    """ Save a signature to disk """
    if self.dirty:
      if verbose:
        puts("Saving {}".format(self.SIGNATURE_FILE_NAME))
      with self.signature_file.open('wb') as stream:
        stream.write(yaml.safe_dump(self.tree, encoding='utf8'))
    self.dirty = False
