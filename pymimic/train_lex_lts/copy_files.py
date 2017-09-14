import os
import argparse
from shutil import copyfile

def parse_args():
    parser = argparse.ArgumentParser(
        description='Helper to setup training of lexicon and LTS rules.')
    parser.add_argument('--builddir', required=True,
                        help='Path to the directory where the lexicon and rules will be built')
    args = parser.parse_args()
    return args


args = parse_args()
builddir = args.builddir
os.makedirs(builddir, exist_ok = True)
datadir = os.path.join(os.path.dirname(__file__), 'data')
files_to_cp = ['huff_table', 'make_lex.scm']
for f in files_to_cp:
    copyfile(os.path.join(datadir, f), os.path.join(builddir, f))


