#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

from source import MediaSourceNode


MIN_PYTHON_VERSION = (3,6)



def cmd_bake(args):
  tree_root = MediaSourceNode(Path(args.source_tree_root[0]), parent=None)
  tree_root.walk()

def cmd_test(args):
  tree_root = MediaSourceNode(Path(args.source_tree_root[0]), parent=None)
  sys.exit("no test yet")



DESCRIPTION = """
Bulklift: a tool for transcoding trees of media into multiple destinations.
""".strip()

EPILOG = """
""".strip()


parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG)

parser.add_argument('--debug', action='store_true',
                    help="debugging output")

subparsers = parser.add_subparsers(dest='subcommand')

sp_test = subparsers.add_parser('test', help="test manifests")
sp_test.set_defaults(func=cmd_test)
sp_test.add_argument('source_tree_root', type=str, nargs=1,
                     help="root path for your source tree; must contain a .bulklift.yaml with root=true")

sp_bake = subparsers.add_parser('bake', help="bake output trees")
sp_bake.set_defaults(func=cmd_bake)
sp_bake.add_argument('source_tree_root', type=str, nargs=1,
                     help="root path for your source tree; must contain a .bulklift.yaml with root=true")




if __name__ == '__main__':

  if sys.version_info < MIN_PYTHON_VERSION:
    sys.exit("Fatal: at least Python {} required".format(
      '.'.join(map(str,MIN_PYTHON_VERSION)))
    )

  args = parser.parse_args()

  try:
    args.func(args)
  except Exception as e:
    if args.debug:
      raise
    else:
      sys.exit("Fatal: {}".format(e))
