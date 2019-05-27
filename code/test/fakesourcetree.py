from pathlib import Path
from base64 import b64decode

from wrappers import SoxWrapper


class FakeSourceTreeDir(object):
  """ Create a basic source tree directory, used in testing """

  def __init__(self, path):
    """ Initialize a fake dir at `base_path` by creating it """
    self.path = path
    path.mkdir(parents=True, exist_ok=True)

  def writeDotFile(self, name='.dotfile.txt', size=256, base_path=None):
    """ Write a dotfile at Path `path` under the base dir with length `size`.
        Returns an absolute Path to the file created. """
    base_path = base_path or self.path
    dotfile_path = self.path / name
    with path.open('w') as f:
      f.write('X' * size)
    return dotfile_path


class FakeSourceTreeAlbum(FakeSourceTreeDir):
  """ Construct a fake tree of source media, used during testing """

  DEFAULT_NAME = "DJ Bulklift - Greatest Hits"
  EMPTY_GIF_DATA = b64decode('R0lGODlhAQABAAAAACH5BAEAAAAALAAAAAABAAEAAAI=')

  def __init__(self, base_path, name=DEFAULT_NAME, filetype='flac',
               n_tracks=10):
    """ Create a fake album within `base_path` """
    album_path = base_path / name
    super(FakeSourceTreeAlbum, self).__init__(path=album_path)
    self.cover_gif = self.writeEmptyGif()
    self.art_dir = self.writeArtDir()
    self.tracks = {}
    for n in range(1, n_tracks+1):
      self.tracks[n] = self.writeAudioFile(self.num2Filename(n, filetype))

  def num2Filename(self, n, filetype):
    """ Synthesize a string filename for track `n` """
    return "{:02d} - Track {}.{}".format(n, n, filetype)

  def writeAudioFile(self, name, base_path=None):
    """ Use Sox to write an audio file at Path `path`.  Returns an absolute
        Path to the file created. """
    base_path = base_path or self.path
    audio_file_path = base_path / name
    sox = SoxWrapper(output_path=audio_file_path)
    sox.run()
    return audio_file_path

  def writeEmptyGif(self, name='cover.gif', base_path=None):
    """ Write an empty 1x1 pixel gif.  Returns an absolute Path to the file
        created. """
    base_path = base_path or self.path
    gif_path = base_path / name
    with gif_path.open('wb') as f:
      f.write(self.EMPTY_GIF_DATA)
    return gif_path

  def writeArtDir(self, name="ArtworkNStuff", base_path=None):
    """ Create a directory inside the album, notionally used to hold extra
        artwork.  Place a couple of gifs inside it to simulate this.  Returns
        an absolute path to the dir created.  """
    base_path = base_path or self.path
    art_dir_path = base_path / 'ArtworkNStuff'
    art_dir_path.mkdir()
    self.writeEmptyGif(name='cover1.gif', base_path=art_dir_path)
    self.writeEmptyGif(name='cover2.gif', base_path=art_dir_path)
    return art_dir_path
