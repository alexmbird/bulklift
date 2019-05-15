import os.path

from transcoders.base import TranscoderBase


class TranscoderCopy(TranscoderBase):

  FILE_EXTENSION = None  # No extension change
  COMMENT = "Bulklift 0.1 (direct copy)"

  def buildTranscodeCmd(self, source_path):
    """ Return a command appropriate for transcoding the specified file """
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
      str(self.outputFilePath(source_path.name))
    ]
