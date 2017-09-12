# -*- coding: utf-8 -*-
"""
Created on Fri Apr  8 01:18:41 2016

@author: sergio
"""

import os
from subprocess import call, STDOUT
from functools import partial
from .utils import progress_bar
from .scheme import parse
from .common import eval_tree
from .common import read_align, read_lts, process_lts, test_lts


def print_lts_desc(featsnp, feat_names, lts_desc_fn):
    with open(lts_desc_fn, "w") as fd:
        print("(", file=fd)
        for i, feat_name in enumerate(feat_names):
            feat_values = sorted(set([x[i] for x in featsnp]))
            print("(" + feat_name, file=fd)
            print(" ".join(feat_values), file=fd)
            print(")", file=fd)
        print(")", file=fd)


def call_wagon(input_fn, output_fn, stop, lts_desc_fn, wagon_path, logfh=None):
    wagon_args = ["-data", input_fn, "-test", input_fn, '-desc',
                  lts_desc_fn, "-stop", str(stop), "-output", output_fn]
    if logfh is not None:
        log_stderr = STDOUT
    else:
        log_stderr = None
    call([wagon_path] + wagon_args, stdout=logfh, stderr=log_stderr)
    return


def build_letter(letter, allowables, featsnp, feat_central, stop,
                 scratchdir, lts_desc_fn, wagon_path):
    feats_np_letter = [x for x in featsnp if x[feat_central] == letter]
    input_fn = os.path.join(scratchdir, "ltsdataTRAIN." + letter + ".feats")
    output_fn = os.path.join(scratchdir, "lts." + letter + ".tree")
    # numpy.savetxt uses latin-1 (we encode text as utf-8). we don't use it
    if len(feats_np_letter) > 0:
        fmt = ["%s", ] * len(feats_np_letter[0])
        fmt = " ".join(fmt)
        with open(input_fn, "w") as fh:
            for row in feats_np_letter:
                fh.write((fmt % tuple(row) + "\n"))
        with open(os.path.join(scratchdir, "wagon_" + letter + ".log"), "w") as wagonlog:
            call_wagon(input_fn, output_fn, stop, lts_desc_fn, wagon_path, logfh=wagonlog)
    else:
        # No features, wagon fails to compute the impurity. We give prob=1 to the first allowed non-epsilon
        with open(output_fn, "w") as fh:
            towrite = sorted(set(allowables) - set("_epsilon_"))
            if len(towrite) > 0:
                weight = 1.0/len(towrite)
                fh.write("((" + " ".join(["(" + " ".join([x, "{}".format(weight)]) + ")" for x in towrite]) + " _epsilon_))")
            else:
                fh.write("((_epsilon))")

def build_lts(allowables, featsnp, feat_names, feat_central, stop,
              scratchdir, wagon_path):
    letters = sorted(set(allowables.keys()) - set("#"))
    lts_desc_fn = os.path.join(scratchdir, "ltsLTS.desc")
    print_lts_desc(featsnp, feat_names, lts_desc_fn)
    build_let = partial(build_letter, featsnp=featsnp,
                        feat_central=feat_central, stop=3,
                        scratchdir=scratchdir, lts_desc_fn=lts_desc_fn,
                        wagon_path=wagon_path)
    for i, letter in enumerate(letters):
        progress_bar(i, len(letters))
        build_let(letter, allowables = allowables[letter])


def read_tree(filename):
    """ This parses a lts_scratch/*.tree file. It contains the decision tree
    trained for a letter."""
    with open(filename, "rt") as fd:
        output = []
        for line in fd.readlines():
            # comment (license, author...)
            if line.startswith(";"):
                continue
            output.append(line)
        all_rules = " ".join(output)
        lts = parse(all_rules)
    return lts

def _simplify_leaf(leaf):
    if not isinstance(leaf, list):
        raise ValueError("Should not happen")
    if len(leaf) == 3 and isinstance(leaf[0][1], str) and leaf[0][1] == "is":
        return [leaf[0], _simplify_leaf(leaf[1]), _simplify_leaf(leaf[2])]
    elif len(leaf) == 1:
        return [x for x in leaf[0] if isinstance(x, str) or (isinstance(x, list) and len(x) == 2 and x[1] != 0)]
    else:
        raise ValueError("Should not happen 2", leaf)

def merge_models(letters, scratchdir):
    lts_rules = []
    for (i, letter) in enumerate(letters):
        progress_bar(i, len(letters))
        tree = read_tree(os.path.join(scratchdir, "lts." + letter + ".tree"))
        lts_rules.append((letter, _simplify_leaf(tree)))
    return lts_rules

def _print_leaf(leaf, fd, indent):
    if len(leaf) == 3 and isinstance(leaf[0][1], str) and leaf[0][1] == "is":
        print(" "*indent + "((" + " ".join([str(x) for x in leaf[0]]) + ")", file=fd)
        _print_leaf(leaf[1], fd, indent + 1)
        _print_leaf(leaf[2], fd, indent + 1)
        print(" "*indent + ")", file=fd)
    else:
        print(" "*indent + "((" + " ".join(["(" + " ".join([str(y) for y in x]) + ")" for x in leaf[0:-1]]) + " " + leaf[-1] + "))", file=fd)

def write_lts(name, lts_rules, output_fn):
    with open(output_fn, "w") as fd:
        print(";; LTS rules", file=fd)
        print("(set! {} '(".format(name), file=fd)
        for (letter, tree) in lts_rules:
            print("({}".format(letter), file=fd)
            _print_leaf(tree, fd, indent=1)
            print(")", file=fd)
        print("))", file=fd)

def load_and_test_lts(align_fn, lts_rules_fn, log_file=None):
    """
    align_fn: Align file to test the LTS model against.
    lts_rules_fn: LTS rules scm file.
    """
    align = read_align(align_fn)
    lts_raw = read_lts(lts_rules_fn)
    lts = process_lts(lts_raw)
    accuracy = test_lts(align, lts, log_file=log_file)
    print("LTS word accuracy on train set (cmulex expected ~60%): {:.1%}".
          format(accuracy))

