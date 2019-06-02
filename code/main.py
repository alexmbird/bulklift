#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path
import subprocess
import os
import shutil
from itertools import chain

from clint.textui import puts, indent, colored

from input import MediaSourceDir
from output import OutputTree
from manifest import Manifest


MIN_PYTHON_VERSION = (3,5,3)



def cmd_transcode(args):
  """ Find any outstanding transcoding jobs and action them """
  puts("Walking media tree...")
  tree_root = MediaSourceDir(Path(args.source_tree_root[0]))
  input_albums = [msd.album() for msd in tree_root.walk() if msd.is_transcodable()]
  for n, ia in enumerate(input_albums):
    puts("{} ({} of {})".format(ia, n+1, len(input_albums)))
    with indent(2):
      ia.transcode()
      puts()
  if args.noclean:
    puts("Skipping cleanup of redundant targets")
  else:
    for oconf in tree_root.manifest.outputs:
      puts("Cleaning up redundant dirs in output tree '{}'".format(oconf['name']))
      otree = OutputTree(Path(oconf['path']))
      with indent(2):
        output_albums = list(chain.from_iterable([ia.output_albums for ia in input_albums]))
        otree.cleanup(expected_dirs=[oa.path for oa in output_albums])


def cmd_edit(args):
  """ Edit the manifest for a directory.  If none exists generate a sensible
      template to start from """
  abspath = Path(args.dir).resolve()
  manifest_path = Manifest.manifestFilePath(abspath)
  puts("Editing manifest for '{}'".format(manifest_path))
  if not manifest_path.exists():
    manifest = Manifest.fromDir(abspath)
    with manifest_path.open('w') as stream:
      stream.write(manifest.dumpTemplate())
  subprocess.run([
    os.environ.get('EDITOR', shutil.which('nano')),
    str(manifest_path)
  ])


parser = argparse.ArgumentParser(
  description="Bulklift: a tool for transcoding your music library.",
  epilog="""
For more information and the latest version see https://github.com/alexmbird/bulklift.
""".strip()
)

parser.set_defaults(func=lambda args: parser.print_help())

parser.add_argument('--debug', action='store_true',
                    help="debugging output")

subparsers = parser.add_subparsers(dest='subcommand')

sp_tc = subparsers.add_parser('transcode', help="transcode audio to output trees")
sp_tc.set_defaults(func=cmd_transcode)
sp_tc.add_argument('--noclean', action='store_true',
                  help="skip removal of redundant albums from output tree(s)")
sp_tc.add_argument('--output', '-o', type=str, default=None,
                   help="single output to work with")
sp_tc.add_argument('source_tree_root', type=str, nargs=1, default='.',
                   help="root path for your source tree; must contain a .bulklift.yaml with root=true.  Default is current dir.")

sp_edit = subparsers.add_parser('edit', help="create/edit a .bulklift.yml manifest")
sp_edit.set_defaults(func=cmd_edit)
sp_edit.add_argument('dir', nargs='?', default='.',
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
      puts(colored.red("Fatal: {}".format(e)))
      sys.exit(1)
