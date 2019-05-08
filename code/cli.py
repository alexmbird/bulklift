import argparse


DESCRIPTION = """
Bulklift: a tool for transcoding trees of media into multiple destinations.
""".strip()

EPILOG = """
""".strip()


parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG)

parser.add_argument('source_tree_root', type=str, nargs=1,
                    help="root path for your source tree; must contain a .bulklift.yaml with root=true")
parser.add_argument('--debug', action='store_true',
                    help="debugging output")
