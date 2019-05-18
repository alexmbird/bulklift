import os.path

from transcoders.base import TranscoderBase


class TranscoderCopy(TranscoderBase):

  FILE_EXTENSION = None  # No extension change
  COMMENT = "Bulklift 0.1 (direct copy)"

  def buildTranscodeCmd(self, source_path):
    """ Return a command appropriate for transcoding the specified file """
    return [
      self.transcode_ffmpeg_path,
      '-y',
      '-loglevel', 'error',
      '-i', str(source_path),
      '-map', '0:a',
      '-bsf:a', 'remove_extra',
      '-codec:a', 'copy',
      *self.ffmpegMetadataOptions(),
      '-codec:v', 'copy',
      str(self.outputFilePath(source_path.name))
    ]
