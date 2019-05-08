#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path
import subprocess
import os
import shutil

from source import MediaSourceDir
from manifest import Manifest


MIN_PYTHON_VERSION = (3,6)



def cmd_bake(args):
  tree_root = MediaSourceDir(Path(args.source_tree_root[0]), parent=None)
  tree_root.walk()


def cmd_test(args):
  tree_root = MediaSourceDir(Path(args.source_tree_root[0]), parent=None)
  sys.exit("no test yet")


def cmd_edit(args):
  abspath = Path(args.dir[0]).resolve()
  manifest_path = Manifest.manifest_file_name(abspath)
  if not manifest_path.exists():
    manifest = Manifest.load(abspath)
    with open(manifest_path, 'w') as stream:
      stream.write(manifest.dumpTemplate())
  subprocess.run([
    os.environ.get('EDITOR', shutil.which('nano')),
    manifest_path
  ])


DESCRIPTION = """
Bulklift: a tool for transcoding your music library.
""".strip()

EPILOG = """
For more information and the latest version see
https://github.com/alexmbird/bulklift.
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

sp_edit = subparsers.add_parser('edit', help="create/edit a .bulklift.yml manifest")
sp_edit.set_defaults(func=cmd_edit)
sp_edit.add_argument('dir', nargs='?', default=['.'],
                     help="path to *directory* whose manifest to edit")


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
