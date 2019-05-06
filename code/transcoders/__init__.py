
from transcoders.copy import TranscoderCopy
from transcoders.opus import TranscoderOpus
from transcoders.lame import TranscoderLame

TRANSCODERS = {
  'copy': TranscoderCopy,
  'opus': TranscoderOpus,
  'lame': TranscoderLame,
}
