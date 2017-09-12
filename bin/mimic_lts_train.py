#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import json
import argparse

from distutils.spawn import find_executable

from pymimic.train_lex_lts.train_lts import (read_lexicon, filter_lexicon, write_lex,
                                    cummulate_pairs,
                                    normalise_table, save_pl_table, align_data,
                                    save_lex_align, build_feat_file)

from pymimic.train_lex_lts.build_lts import build_lts, merge_models, write_lts, load_and_test_lts
from pymimic.train_lex_lts.lts_to_c import lts_to_c

WAGON = os.getenv("WAGON")
if WAGON is None or not os.path.exists(WAGON):
    WAGON = find_executable("wagon")

WFST_BUILD = os.getenv("WFST_BUILD")
if WFST_BUILD is None or not os.path.exists(WFST_BUILD):
    WFST_BUILD = find_executable("wfst_build")

def parse_args():
    def parse_json(infile):
        try:
            with open(infile, "r") as fd:
                output = json.load(fd)
                return output
        except:
            raise argparse.ArgumentTypeError("Error loading json file {}".format(infile))

    parser = argparse.ArgumentParser(description='Train Letter To Sound rules')
    parser.add_argument('--lexicon', dest='lexicon', action='store',
                        required=True, help='The lexicon that will be used to train the rules')
    parser.add_argument('--lexicon-fmt-flat', dest='lexicon_fmt_flat', action='store_true',
                        help='The lexicon format is flat (no syllables)')
    parser.add_argument('--lexicon-fmt-noflat', dest='lexicon_fmt_flat', action='store_false')
    parser.set_defaults(lexicon_fmt_flat=False)
    parser.add_argument("--lang-prefix", dest="prefix", action="store", required=True,
                        help="Prefix for the lexicon, typically the language code (e.g. 'cmu', 'fr')")
    parser.add_argument("--filter-remove-shorter-than", dest="minlength", action="store",
                        required=False, default=4,
                        help="Before training the LTS rules, prune the lexicon with words with less than this number of characters")
    parser.add_argument("--filter-lowercase", dest="tolower", action="store",
                        required=False, default=True,
                        help="Before training the LTS rules, lowercase words in lexicon")
    parser.add_argument("--filter-invalid-letters", dest="invalid_letters", action="store",
                        required=False, default=True,
                        help="Before training the LTS rules, remove words with invalid letters in lexicon")
    parser.add_argument("--wagon-stop", dest="wagon_stop", action="store",
                        required=False, default=3,
                        help="When building the LTS rules, the minimum number of samples for leaf nodes")
    parser.add_argument('--allowables', dest='allowables', action='store', type=parse_json,
                        required=True, help='The path to the allowables json file')
    default_feat_names = ['Relation.LTS.down.name',
                          'p.p.p.p.name ignore',
                          'p.p.p.name',
                          'p.p.name',
                          'p.name',
                          'name',
                          'n.name',
                          'n.n.name',
                          'n.n.n.name',
                          'n.n.n.n.name ignore',
                          'pos ignore']
    parser.add_argument('--feat-names', dest='feat_names', action='store', required=False,
                        type=parse_json, default=default_feat_names)
    args = parser.parse_args()
    return args

def main():
    WORK_DIR = os.getcwd()
    args = parse_args()
    LEX_LTS_PREFIX = args.prefix
    # Filtered lexicon:
    # lex_entries is essentially the lexicon with short words removed and
    # with lower case. lex_entries is more suitable than the raw lexicon for
    # training LTS rules
    minlength = args.minlength  # Remove short words (len<4)
    lower = args.tolower  # Lowercase words
    # LTS Rule wagon stop
    wagon_stop = args.wagon_stop

    # The input lexicon:
    lexicon_fn = args.lexicon
    lexicon_is_flat = args.lexicon_fmt_flat

    feat_names = args.feat_names
    feat_central = feat_names.index('name')  # 5

    LTS_SCRATCH = os.path.join(WORK_DIR, "{}_lts_scratch".format(LEX_LTS_PREFIX))
    lts_rules_fn = os.path.join(WORK_DIR, "{}_lts_rules.scm".format(LEX_LTS_PREFIX))

    # Intermediate and final files and directories:
    lex_entries_fn = os.path.join(LTS_SCRATCH, "lex_entries.out")
    lex_pl_tablesp_fn = os.path.join(LTS_SCRATCH, "lex-pl-tablesp.scm")
    lex_align_fn = os.path.join(LTS_SCRATCH, "lex.align")
    failed_align_fn = os.path.join(LTS_SCRATCH, "failed_align.txt")
    lex_feats_fn = os.path.join(LTS_SCRATCH, "lex.feats")
    rgdir = os.path.join(WORK_DIR, "{}_wfst".format(LEX_LTS_PREFIX))
    c_dir = os.path.join(WORK_DIR, "{}_c".format(LEX_LTS_PREFIX))


    # Script:
    os.makedirs(LTS_SCRATCH, exist_ok=True)


    print("1. Load lexicon in festival format")
    lexicon = read_lexicon(lexicon_fn, is_flat=lexicon_is_flat, append_stress_to=[])
    print("2. Filter lexicon: Removing short words and converting to lower case")
    filtered_lex = filter_lexicon(lexicon, minlength=minlength, lower=lower, allowables = args.allowables,
                                  remove_invalid_letters = args.invalid_letters)
    #write_lex(filtered_lex, lex_entries_fn, flattened=True)

    print("3. Align lexicon")
    print("3.1. Count probabilities of letter-phone pairs")
    (pl_table, align_failed) = cummulate_pairs(filtered_lex, args.allowables)
    with open(failed_align_fn, "w") as fd:
        print(json.dumps(align_failed, indent = 4, ensure_ascii=False), file=fd)
    pl_table_norm = normalise_table(pl_table)
    #save_pl_table(pl_table_norm, lex_pl_tablesp_fn)  # sort dict by value sorted(d, key=d.get)
    print("3.2. Align letters with phones")
    (good_align, align_failed) = align_data(filtered_lex, pl_table_norm)
    save_lex_align(good_align, lex_align_fn)
    print("3.3 Build feat file")
    feats = build_feat_file(good_align, lex_feats_fn)

    print("4. Build LTS models")
    # Build LTS

    build_lts(args.allowables, feats, feat_names, feat_central=feat_central,
              stop=wagon_stop, scratchdir=LTS_SCRATCH, wagon_path=WAGON)
    print("5. Merge LTS models")
    all_letters = sorted(set(args.allowables.keys()) - set("#"))
    lts_model = merge_models(all_letters, LTS_SCRATCH)
    write_lts("{}_lts_rules".format(LEX_LTS_PREFIX), lts_model, lts_rules_fn)
    print("6. Test LTS model")
    load_and_test_lts(lex_align_fn, lts_rules_fn)
    print("7. Convert LTS to C code:")
    lts_to_c(LEX_LTS_PREFIX, lts_model, rgdir=rgdir, wfstdir=rgdir, wfst_build=WFST_BUILD, c_dir=c_dir)

if __name__ == "__main__":
    main()

