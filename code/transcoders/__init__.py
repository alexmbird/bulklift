
from .base import TRANSCODE_TYPES
from transcoders.copy import TranscoderCopy
from transcoders.opus import TranscoderOpus
from transcoders.lame import TranscoderLame

TRANSCODERS = {
  'copy': TranscoderCopy,
  'opus': TranscoderOpus,
  'lame': TranscoderLame,
}

__all__ = [TRANSCODERS, TRANSCODE_TYPES]
