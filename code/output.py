import shutil
from pathlib import Path

from clint.textui import colored, puts, indent

from util.file import is_parent_path, filename_matches_globs, \
  AUDIO_FORMATS, AUDIO_FORMATS_LOSSLESS, IMAGE_FORMATS
from util.sanitize import FILENAME_SANITIZERS

from manifest import MetadataError
from wrappers import R128gainWrapper
from signature import Signature
from handlers import FORMAT_HANDLERS, OutputHandlerCopy


class OutputTree(object):
  """ Represent a whole Bulklift output tree with various functionality to
      garden it  """

  def __init__(self, root_path):
    """ Initialize TargetTree rooted at a specific path """
    super(OutputTree, self).__init__()
    self.root_path = root_path

  def cleanup(self, expected_dirs, verbose=True):
    """ Remove any dirs from the target tree that aren't a member of
        expected_dirs or their parent paths. Root of tree is left untouched. """
    def clean(victim, root=False):
      for entry in victim.iterdir():
        if entry.is_dir():
          clean(entry)
      if not root:
        if not any(map(lambda ed: is_parent_path(victim, ed), expected_dirs)):
          if verbose:
            puts(colored.red("Removing '{}'".format(victim)))
          shutil.rmtree(str(victim), ignore_errors=True)
    clean(self.root_path, root=False)

  def permissions(self, file_mode, dir_mode, user, group):
    """ Fix permissions on the target tree to match mode/user/group """
    raise NotImplementedError()


class OutputAlbum(object):
  """ Represent a single output album """

  def __init__(self, mconfig, oconfig, metadata):
    """ Initialize an OutputAlbum.  `metadata` a dict of metadata replacements
        to have ffmpeg do.  """
    super(OutputAlbum, self).__init__()
    self.mconfig = mconfig     # config section
    self.oconfig = oconfig     # this specific output
    self.sanitize = FILENAME_SANITIZERS[oconfig['sanitize_paths']]
    self.path = self.albumPath(metadata)
    self.artwork = []
    self.dirty = False  # media has changed; need to re-run r128gain
    self.signature = Signature(self.path, mconfig, oconfig, metadata)
    self.contents = []  # all *filenames* this dir should contain

  def albumPath(self, metadata):
    """ Return the output path for this album """
    tconf = self.mconfig['target']
    try:
      album_dir = Path(tconf['album_dir'].format(**metadata))
    except KeyError:
      raise MetadataError("Failed to interpolate template '{}' with metadata: {}".format(
        tconf['album_dir'], metadata
      ))
    return Path(self.oconfig['path']) / self.sanitize(album_dir)

  @property
  def output_name(self):
    return self.oconfig['name']

  def isFilterAllowed(self, potential):
    """ Return True if potential is allowed by filters, False otherwise.
        Include filter takes priority.  """
    f_include = self.oconfig['filters']['include']
    if f_include and not filename_matches_globs(potential, f_include):
      return False
    f_exclude = self.oconfig['filters']['exclude']
    if f_exclude and filename_matches_globs(potential, f_exclude):
      return False
    return True

  def prepare(self, verbose=True):
    """ Prepare the output album for writing """
    if verbose:
      puts("Creating output dir {}".format(self.path))
    self.path.mkdir(parents=True, exist_ok=True)

  def finalize(self, verbose=True):
    """ If we've made any changes to the output dir finalize the album by
        adding artwork and signature + running r128gain """
    if self.dirty:
      if verbose:
        puts("Finalizing for output '{}' @ {}".format(self.output_name, self.path))
      with indent(2):
        self.copyArtwork(verbose=verbose)
        self.removeOrphans(verbose=verbose)
        self.signature.clean(verbose=verbose)
        self.r128gain(verbose=verbose)
        self.signature.save(verbose=verbose)
        self.dirty = False

  def copyArtwork(self, verbose=True):
    """ Clone a file (typically artwork) into the album dir.  This is a simple
        bit-perfect copy, not an ffmpeg passthrough.  """
    if verbose:
      puts("Cloning artwork...")
    with indent(2):
      for source_path in self.artwork:
        output_path = self.path / source_path.name
        if self.signature.is_valid(output_path.name, source_path, None):
          pass
        else:
          if verbose:
            puts("Copying '{}'".format(source_path.name))
          output_path = self.path / source_path.name
          shutil.copy(str(source_path), str(output_path))
          self.signature.add(output_path.name, source_path, codec=None)

  def removeOrphans(self, verbose=True):
    """ Remove any orphaned files, i.e. not mentioned in the signature.
        Directories are ignored.  """
    if verbose:
      puts("Removing orphaned files from {}...".format(self.output_name))
    with indent(2):
      for p in self.path.iterdir():
        if p.is_file() and p.name != Signature.SIGNATURE_FILE_NAME:
          if p.name not in self.contents:
            if verbose:
              puts(colored.red("Removing orphan '{}'".format(p)))
            p.unlink()

  def r128gain(self, verbose=True):
    """ Run r128gain over the output dir """
    rconf = self.mconfig['r128gain']
    tconf = self.mconfig['transcoding']
    if rconf['type'] in (None, False, 'null'):
      if verbose:
        puts("r128gain disabled for this album")
      return
    r128 = R128gainWrapper(
      target_dir=self.path,
      album_gain=rconf['type'] == 'album',
      threads=rconf['threads'],
      ffmpeg_binary=rconf['ffmpeg_path'] or tconf['ffmpeg_path'],
      binary=rconf['r128gain_path']
    )
    if verbose:
      puts("Running r128gain for output {} ({} mode)...".format(
        self.output_name, rconf['type'])
      )
    r128.run(output=False)

  def incorporate(self, source_path, ffmpeg):
    """ Given Path `source_path`, if it is wanted in our output add it to the
        encoding job wrapped by `ffmpeg`.  Metadata isn't required as `ffmpeg`
        already has it.  """
    sig = self.signature
    ext = source_path.suffix.lstrip('.').lower()
    if ext in IMAGE_FORMATS:            # clone artwork later
      self.artwork.append(source_path)  # hmmm not getting sanitized
      self.contents.append(source_path.name)
      return
    if ext not in AUDIO_FORMATS:
      return
    if not self.isFilterAllowed(source_path):  # audio not wanted; quit early
      return

    desired = self.oconfig['formats'][0]
    if ext in self.oconfig['formats'] or desired == 'copy':
      handler_class = OutputHandlerCopy
    elif ext in AUDIO_FORMATS_LOSSLESS:
      try:
        handler_class = FORMAT_HANDLERS[desired]
      except KeyError:
        raise ValueError("Your primary format ('{}') isn't one I can transcode to".format(ext))
    else:
      return  # unsupported format for this media; skip it

    # If we reach this point we know how to transcode the media
    h = handler_class(source_path, self.path, self.oconfig, self.sanitize)
    self.contents.append(h.output_name)
    if sig.is_valid(h.output_name, source_path, h.FILE_EXTENSION):
      pass # present and correct
    else:
      h.addToFFmpeg(ffmpeg)
      # It is confusing to add to the signature before ffmpeg has created the
      # output.  Refactor with queued operation objects so we can trigger it
      # as part of a later finalize()
      sig.add(h.output_name, source_path, h.FILE_EXTENSION)
      self.dirty = True
