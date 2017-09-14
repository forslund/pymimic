#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LTS rules training based on festival/lib/lts_build.scm script

Author: Sergio Oller, 2016
"""
from __future__ import unicode_literals
from __future__ import print_function
import copy
from collections import defaultdict

from .common import read_lexicon, write_lex
from .utils import progress_bar, logger


def filter_lexicon(lexicon, minlength=4, lower=True, allowables=None,
                   remove_invalid_letters = False):
    logger.info("Filtering lexicon...")
    filtered_lex = defaultdict(list)
    num_words = len(lexicon.keys())
    all_letters = None
    if remove_invalid_letters:
        if allowables is None:
            raise ValueError("Missing allowables")
        all_letters = set(allowables.keys())
    for iw, word in enumerate(lexicon.keys()):
        progress_bar(iw, num_words)
        word_filtered = word
        if minlength is not None and len(word) < minlength:
            continue
        if lower is True:
            word_filtered = word_filtered.lower()
        if remove_invalid_letters:
            word_filtered = word_filtered.lower()
            if len(set(word_filtered) - all_letters) > 0:
                continue
        filtered_lex[word_filtered] = lexicon[word]
    return filtered_lex


def load_and_filter_lex_for_lts(lexicon_fn, filtered_lex_fn=None,
                                minlength=4, lower=True, append_stress_to=[]):
    """ We load the raw lexicon and return a lexicon with words with more than
        three characters. Ideally we could leave nouns, verbs and adjectives as
        the unknown words we will find will probably belong to one of those
        categories.
        See: http://www.festvox.org/docs/manual-2.4.0/festival_13.html#Building-letter-to-sound-rules
    """
    lexicon = read_lexicon(lexicon_fn, is_flat=False, append_stress_to=append_stress_to)
    filtered_lex = filter_lexicon(lexicon, minlength=minlength, lower=lower)
    if filtered_lex_fn is not None:
        write_lex(filtered_lex, filtered_lex_fn, flattened=True)
    return filtered_lex


def valid_pair(phone, letter, pl_table):
    if letter in pl_table.keys() and phone in pl_table[letter].keys():
        return True
    return False


def valid_pair_e(phone, nphone, letter, pl_table):
    if (letter in pl_table.keys() and
            (phone + "-" + nphone) in pl_table[letter].keys()):
        return True
    return False


def find_all_aligns(phones, letters, pl_table):
    """Find all feasible alignments."""
    r = []
    if (len(phones) == 1 and len(letters) == 1 and
            phones[0] == letters[0] and phones[0] == '#'):
        return [[('#', '#')]]
    if valid_pair('_epsilon_', letters[0], pl_table):
        all_left = find_all_aligns(phones, letters[1:], pl_table)
        r += [[('_epsilon_', letters[0])] + x for x in all_left]
    if valid_pair(phones[0], letters[0], pl_table):
        all_left = find_all_aligns(phones[1:], letters[1:], pl_table)
        r += [[(phones[0], letters[0])] + x for x in all_left]
    # Hmm, change this to always check doubles
    try:
        if (len(phones) > 1 and
                valid_pair_e(phones[0], phones[1], letters[0], pl_table)):
            all_left = find_all_aligns(phones[2:], letters[1:], pl_table)
            two_phones = phones[0] + "-" + phones[1]
            r += [[(two_phones, letters[0])] + x for x in all_left]
    except:
        print(phones)
        print(letters)
        raise
    return r


def cummulate(phone, letter, pl_table):
    "record the alignment of this phone and letter."
    if (phone == letter or (phone != "#" and letter != "#")):
        score = 1.0
        if phone == "_epsilon_":
            score = 0.1
        pl_table[letter][phone] += score
    return


def cummulate_aligns(all_aligns, pl_table):
    for align in all_aligns:
        for (phone, letter) in align:
            cummulate(phone, letter, pl_table)
    return


def cummulate_pairs(lexicon, allowables):
    failed_aligns = 0
    count_all_aligns = 0
    failed_list = []
    # initialize pl_table of letter-phone counts
    pl_table = defaultdict(lambda: defaultdict(int))
    for letter, phones in allowables.items():
        for phone in phones:
            pl_table[letter][phone] = 0
    for i, (word, heteronyms) in enumerate(sorted(lexicon.items())):
        progress_bar(i, len(lexicon.keys()))
        for heteronym in heteronyms:
            # pos = heteronym[0]
            # phones_in_syl = heteronym[1]
            phones = heteronym[2]
            # add word boundaries:  # enworden(wordexplode(word))
            bound_phones = ['#'] + phones + ['#']
            bound_word = ['#'] + list(word) + ['#']
            try:
                all_aligns = find_all_aligns(bound_phones,
                                             bound_word,
                                             pl_table)
            except:
                print(bound_word)
                print(bound_phones)
                raise
            if len(all_aligns) == 0:
                failed_aligns += 1
                failed_list.append((word, " ".join(phones)))
            cummulate_aligns(all_aligns, pl_table)
            count_all_aligns += 1
    logger.debug("\n".join([": ".join(x) for x in failed_list]))
    logger.info("Failed aligns: {}/{}".format(failed_aligns, count_all_aligns))
    return (pl_table, failed_list)


def normalise_table(pl_table):
    "Change scores into probabilities."
    pl_table_norm = copy.deepcopy(pl_table)
    for letter in pl_table_norm.keys():
        all_counts = sum(pl_table_norm[letter].values())
        for phone in pl_table_norm[letter].keys():
            if all_counts == 0:
                pl_table_norm[letter][phone] = 0
            else:
                pl_table_norm[letter][phone] /= all_counts
    return pl_table_norm


def save_pl_table(pl_table, output_fn):
    with open(output_fn, "wt") as fd:
        print("(set! pl-table'", file=fd)
        for ilet, letter in enumerate(sorted(pl_table.keys())):
            if ilet == 0:
                print("(", file=fd, end="")
            else:
                print(" ", file=fd, end="")
            print("({}".format(letter), file=fd)
            num_phones = len(pl_table[letter].keys())
            for iphone, (phone, value) in \
                    enumerate(sorted(pl_table[letter].items())):
                myline = "  (" + phone + " . " + str(value) + ")"
                if iphone == num_phones-1:
                    myline += ")"
                print(myline, file=fd)
        print("))", file=fd)


def load_and_cummulate_pairs(lexicon_fn, allowables, output_fn):
    lexicon = read_lexicon(lexicon_fn, is_flat=True)
    logger.info("Count probabilities of letter-phone pairs")
    pl_table = cummulate_pairs(lexicon, allowables)
    pl_table_norm = normalise_table(pl_table)
    save_pl_table(pl_table_norm, output_fn)
    return pl_table_norm


def score_pair(phone, letter, pl_table):
    """
    Give score for this particular phone letter pair.
    """
    try:
        return pl_table[letter][phone]
    except KeyError:
        return 0


def find_best_alignment(phones, letters, pl_table,
                        path=None, score=0, fba=None):
    """
    Find all feasible alignments.
    """
    if path is None:
        path = []
    if fba is None:
        fba = dict(path=[], score=0, score_epsilon=0)
    if letters is None or len(letters) == 0:
        if score > fba['score']:
            fba['score'] = score
            fba['path'] = path[::-1]
            fba['score_epsilon'] = sum([i for (i, (ph, let)) in enumerate(fba['path']) if ph == "_epsilon_"])
        elif score == fba['score']:
            score_epsilon_current = sum([i for (i, (ph, let)) in enumerate(path[::-1]) if ph == "_epsilon_"])
            if score_epsilon_current > fba['score_epsilon']:
                fba['score'] = score
                fba['path'] = path[::-1]
                fba['score_epsilon'] = score_epsilon_current
        return fba
    if valid_pair('_epsilon_', letters[0], pl_table):
        fba = find_best_alignment(phones, letters[1:], pl_table,
                                  [('_epsilon_', letters[0])] + path,
                                  score + score_pair('_epsilon_', letters[0], pl_table),
                                  fba=fba)
    if valid_pair(phones[0], letters[0], pl_table):
        fba = find_best_alignment(phones[1:], letters[1:], pl_table,
                                  [(phones[0], letters[0])] + path,
                                  score + score_pair(phones[0], letters[0], pl_table),
                                  fba=fba)
    if len(phones) > 1 and valid_pair_e(phones[0], phones[1], letters[0], pl_table):
        fba = find_best_alignment(phones[2:], letters[1:], pl_table,
                                  [(phones[0] + "-" + phones[1],
                                    letters[0])] + path,
                                  score + score_pair(phones[0] + "-" +
                                                     phones[1], letters[0], pl_table),
                                  fba=fba)
    return fba



def save_info(pos, path, of):
    """
    Save the best path in a file
    pos = "nil"
    path: [('#', '#'), ('_epsilon', 'a'), ('aa1', 'a'), ... ]
    saves:
    ( ( a a b e r g ) nil _epsilon_ aa1 b _epsilon_ er0 g )
    """
    # 
    # path[1:-1] <- drops ("#", "#")
    # x[1]
    letters = " ".join(x[1] for x in path[1:-1])
    phones = " ".join(x[0] for x in path[1:-1])
    print("( ( " + letters + " ) " + pos + " " + phones + " )", file=of)
    return


def align_data(lexicon, pl_table):
    """
    Aligns characters of each lexicon entry with their phonetic representation.
    """
    align_failed = []
    align_good = []
    num_words = len(lexicon.keys())
    for i, (word, heteronyms) in enumerate(sorted(lexicon.items())):
        progress_bar(i, num_words)
        bound_word = ['#'] + list(word) + ['#']
        for heteronym in heteronyms:
            phones = heteronym[2]
            bound_phones = ['#'] + phones + ['#']
            fba = find_best_alignment(bound_phones, bound_word, pl_table)
            best_path = fba['path']
            if len(best_path) == []:
                align_failed.append((word, heteronym))
            else:
                pos = heteronym[0]
                align_good.append((pos, best_path))
    return (align_good, align_failed)


def save_lex_align(align_good, filename):
    with open(filename, "wt") as ofd:
        for (pos, best_path) in align_good:
            save_info(pos, best_path, ofd)
    return


def build_feat_file(align, feat_file=None):
    feats = []
    for i, (pos, let_phone_list) in enumerate(align):
        progress_bar(i, len(align))
        lets = ["0"]*4 + [x[1] for x in let_phone_list] + ["0"]*4
        phones = [x[0] for x in let_phone_list[1:-1]]
        for i, phone in enumerate(phones):
            j = i + 5
            feats.append([phone]+lets[(j-4):(j+5)] + [pos])
    if feat_file is not None:
        write_feats(feats, feat_file)
    return feats


def write_feats(feats, feat_file):
    with open(feat_file, "w") as ofd:
        for feat in feats:
            print(" ".join([str(x) for x in feat]), file=ofd)

