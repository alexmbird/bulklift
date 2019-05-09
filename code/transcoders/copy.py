import os.path

from util import dict_deep_get

from transcoders.base import TranscoderBase


class TranscoderCopy(TranscoderBase):

  COMMENT = "Bulklift 0.1 (direct copy)"

  def outputFileName(self, source_file):
    """ In copy mode the filename doesn't change """
    return source_file


  def buildTranscodeCmd(self, source_path):
    """ Return a command appropriate for transcoding the specified file """
    target_path = self.output_album_path / source_path.name
    return [
      self.ffmpeg_path,
      '-y', '-loglevel', 'error',
      '-i', str(source_path),
      '-c:v', 'copy',
      '-codec:a', 'copy',
      '-map_metadata', '0',
      '-id3v2_version', '3',
      '-write_id3v1', '1',
      '-metadata', 'comment={}'.format(self.COMMENT),
      str(target_path)
    ]
