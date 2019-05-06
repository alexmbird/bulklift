#!/usr/bin/env python3

import sys
import shutil

from cli import parser
from source import MediaSourceNode, ConfigError
from util import is_executable


if __name__ == '__main__':
  args = parser.parse_args()

  try:
    tree_root = MediaSourceNode(args.source_tree_root[0], parent=None)
  except ConfigError:
    sys.exit("Fatal: missing {} at root of your source tree".format(MediaTreeSourceConfig.CONFIG_YAML_NAME))

  # Check specified binaries are present & executable
  for binary in tree_root.config['config']['binaries'].values():
    if not is_executable(binary):
      sys.exit("Fatal: configured binary '{}' is missing".format(binary))

  tree_root.walk()
