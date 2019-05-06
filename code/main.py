#!/usr/bin/env python3

import sys
import shutil

from cli import parser
from source import MediaSourceNode
from util import is_executable


if __name__ == '__main__':
  args = parser.parse_args()
  tree_root = MediaSourceNode(args.source_tree_root[0], parent=None)
  tree_root.walk()
