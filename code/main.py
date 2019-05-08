#!/usr/bin/env python3

import sys
from pathlib import Path

from cli import parser
from source import MediaSourceNode


MIN_PYTHON_VERSION = (3,6)


if __name__ == '__main__':

  if sys.version_info < MIN_PYTHON_VERSION:
    sys.exit("Fatal: at least Python {} required".format(
      '.'.join(map(str,MIN_PYTHON_VERSION)))
    )

  args = parser.parse_args()

  try:
    tree_root = MediaSourceNode(Path(args.source_tree_root[0]), parent=None)
    tree_root.walk()
  except Exception as e:
    if args.debug:
      raise
    else:
      sys.exit("Fatal: {}".format(e))
