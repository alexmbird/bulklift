import os.path
from pathlib import Path
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

from clint.textui import indent, puts, colored

from manifest import Manifest, MetadataError
from wrappers import FFmpegWrapper, NothingToDoError
from output import OutputAlbum


class TranscodingError(Exception):
  "Failure within a transcoding job"


class MediaSourceDir(object):
  """ A single directory within the media source tree, which may or may not be
      an album to transcode.  """

  def __init__(self, path):
    """ Initialize the MediaSourceDir given its path  """
    self.path = Path(path).resolve()  # resolve() is important - keep it!
    self.manifest = Manifest.fromDir(path)

  def walk(self):
    """ Recursively walk our tree, yielding a MediaSourceDir for every
        subdirectory we find.  """
    for p in self.path.iterdir():
      if p.is_dir() and not p.name.startswith('.'):
        yield from self.__class__(p).walk()
    if self.is_transcodable():
      yield self

  def is_transcodable(self):
    return self.manifest.exists() and len(self.manifest.outputs_enabled) > 0

  def album(self):
    """ Return an InputAlbum for this source dir or raise ValueError if it
        isn't transcodable.  """
    if not self.is_transcodable():
      raise ValueError("Only transcodable dirs can have an album")
    return InputAlbum(
      self.path,
      mconf=self.manifest['config'], oconfs=self.manifest.outputs_enabled,
      metadata=self.manifest['metadata']
    )


class InputAlbum(object):
  """ Represent a single dir of files we may transcode """

  def __init__(self, path, mconf, oconfs, metadata):
    """ Initialize InputAlbum and setup its outputs.  `metadata` is straight
        from the manifest; replacements are applied here.   """
    self.path = path
    self.transcoding_threads = mconf['transcoding']['threads']
    self.metadata_rewrites = self.bakeMetadata(
      metadata, mconf['transcoding']['rewrite_metadata']
    )
    self.output_albums = [
      OutputAlbum(mconf, oconf, metadata) for oconf in oconfs if oconf['enabled']
    ]

  def files(self):
    """ Return list of valid files in the source directory.  The sorting order
        is designed to process the larger files first, leaving smaller jobs to
        soak up empty cores at the end.  The middle element is moved to the top"""
    candidates = list(filter(
      lambda c: c.is_file() and not c.name.startswith('.'),
      self.path.iterdir()
    ))
    candidates.sort(reverse=True, key=lambda c: c.stat().st_size)
    if len(candidates) > 2:
      candidates.insert(1, candidates.pop(int(len(candidates) / 2)))
    return candidates

  def bakeMetadata(self, metadata, rewrites):
    """ Assemble the set of metadata rewrites """
    none_to_str = lambda s: '' if s is None else s
    metadata = {k : none_to_str(v) for k, v in metadata.items()}
    rewritten = {}   # dict comprehension would prevent raising meaningful err
    for k, tpl in rewrites.items():
      if tpl is not None:
        try:
          rewritten[k] = tpl.format(**metadata)
        except KeyError:
          raise MetadataError(
            "{}: a metadata field required by template '{}' is missing".format(
              self.path, tpl
            )
          )
    return rewritten

  def transcode(self, verbose=True):
    """ Generate the desired output albums from this source """
    ffmpeg_jobs = []
    def do_job(j):
      if verbose:
        puts("Transcoding {} ({:d} outputs)".format(j.source_path.name, len(j)))
      j.run()
    for potential in self.files():
      # puts('potential: {}'.format(potential))
      ffmpeg = FFmpegWrapper(
        source_path=potential, metadata=self.metadata_rewrites
      )
      for oa in self.output_albums:
        oa.incorporate(potential, ffmpeg)
      if len(ffmpeg) > 0:  # outputs are expected
        ffmpeg_jobs.append((oa, ffmpeg))

    with ThreadPoolExecutor(max_workers=self.transcoding_threads) as pool:
      futures = [pool.submit(do_job, ffmpeg) for oa, ffmpeg in ffmpeg_jobs]
      try:
        pool.shutdown()
      except KeyboardInterrupt as e:
        for future in futures:
          future.cancel()
        # Re-raising the exception blows up threading.  Make new one.
        raise TranscodingError("Keyboard interrupt; aborted transcoding")

    for oa in self.output_albums:
      oa.finalize(verbose=verbose)

  def __str__(self):
    return "<{} {}>".format(self.__class__.__name__, self.path)
