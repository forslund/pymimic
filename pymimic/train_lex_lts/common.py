#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script is able to:

- Filter a lexicon removing short words not suitable for LTS rules training.
- Test the performance of a LTS rules model, given a lexicon.
- Prune a lexicon with entries that are predicted correctly by an LTS model

Author: Sergio Oller, 2016
"""
from __future__ import unicode_literals
from __future__ import print_function
from codecs import open
import os

from .scheme import parse
from .utils import progress_bar, logger
from collections import defaultdict


def read_raw_lexicon(filename):
    """ Reads a lexicon in Festival format
    The festival format consists of a text file with one entry per line.
    Each entry has three parts:
        - the word, quoted
        - an optional Part Of Speech
        - The syllabification and phonetic transcription
    Example:
      ("hello" nil (((hh ax) 0) ((l ow) 1)))

    The formatting corresponds to a scheme list, so a scheme interpreter is
    required. We use don't use a full scheme interpreter, but it is enough to
    cover our needs.
    """
    with open(filename, "rt") as fd:
        line = fd.readline().rstrip()
        if line != "MNCL":
            yield parse(line)
        for line in fd:
            if line.rstrip() == "":
                continue
            yield parse(line)


def read_lexicon(filename, is_flat=False, append_stress_to=[]):
    """ Converts the lexicon, as parsed by read_lexicon into a
    word->[(part of speech1, phones in syllables1, phones1),
           (part of speech2, phones in syllables2, phones2), ...] dictionary.
    is_flat: False if filename has entries like ("word" pos ( ((a l) 1) ((p e) 0)))
             True if filename has entries like ("word" pos (a1 l p e0))
    append_stress_to: if is_flat is False, to which phones should we add the stress (typically to vocalic phonemes)
    """
    output = defaultdict(list)
    total_bytes = os.path.getsize(filename)
    bytes_read = 0
    for line in read_raw_lexicon(filename):
        try:
            bytes_read += len(line)
            word = line[0]
            pos = line[1]
            syls = line[2]
            if not is_flat:
                flattened_syls = flatten_syls(syls, append_stress_to=append_stress_to)
            else:
                flattened_syls = syls
                syls = None
            output[word].append((pos, syls, flattened_syls))
        except:
            raise ValueError("Malformed line:", line)
            progress_bar(bytes_read, total_bytes)
    return output


def read_raw_align(filename):
    """ Reads a lex.align """
    with open(filename, "rt") as fd:
        line = fd.readline().rstrip()
        if line != "MNCL":
            yield parse(line)
        for line in fd:
            yield parse(line)


def read_align(filename):
    """ Converts the align, as parsed by read_align into a
    word->[(part of speech1, phones in syllables1, phones1),
           (part of speech2, phones in syllables2, phones2), ...] dictionary.
    """
    output = []
    for line in read_raw_align(filename):
        word = line[0]
        pos = line[1]
        phones = line[2:]
        output.append([word, pos, phones])
    return output


def flatten_syls(syls, append_stress_to):
    """ This flattens the syllabification, and marks vowels with the
    corresponding stress mark (vowels given as a list of phonemes in append_stress_to)"""
    output = []
    for syl in syls:
        try:
            phones = syl[0]
            stressed = syl[1]
        except:
            raise ValueError("Unexpected syllable:", syl)
        for phone in phones:
            if phone[0] in append_stress_to:
                output.append(phone + str(stressed))
            else:
                output.append(phone)
    return output


def read_lts(filename):
    """ This parses a _lts_rules.scm file. It contains the decision tree
    that is used to map words not present in the lexicon to phonemes."""
    with open(filename, "rt") as fd:
        output = []
        for line in fd.readlines():
            # comment (license, author...)
            if line.startswith(";"):
                continue
            # variable declaration, We don't need it:
            if line.startswith("(set!"):
                continue
            output.append(line)
        # A first parenthesis is added because the (set! line has a
        # parenthesis that we want to keep.
        all_rules = "(" + " ".join(output)
        lts = parse(all_rules)
    return lts


def process_lts(lts):
    """
    The letter to sound rules are a set of decision trees trained to predict
    the phoneme that corresponds to a given character, considering the three
    previous characters and the three following characters.

    This function returns a dictionary. The keys of the dictionary are the
    letters. The values are the decision trees for each letter, expressed
    as a lambda function that takes as input a word and an index and returns
    the phoneme associated to that word[index] in its context.
    """
    output = dict()
    for character_tree in lts:
        character = character_tree[0]
        tree = character_tree[1]
        tree_lambda = eval_tree(tree)
        output[character] = tree_lambda
    return output


def eval_tree(tree):
    """ This function takes an LTS tree as parsed by the scheme interpreter
    and returns a lambda function. The lambda function takes a word and an
    index returning the phoneme associated to that word[index].
    """
    # non-final node: Depending on condition we follow one branch or another
    if len(tree) == 3:
        condition = eval_condition(tree[0])
        fun_yes = eval_tree(tree[1])
        fun_no = eval_tree(tree[2])
        return (lambda word, index: fun_yes(word, index) if
                condition(word, index) else fun_no(word, index))
    # final node, we take the most option with highest probability
    elif len(tree) == 1:
        return lambda word, index: tree[0][-1]
    else:
        # should not happen
        raise NotImplementedError("Tree: {}".format(tree))


def eval_condition(condition):
    "Generates a lambda function for a condition in the scheme decision tree"
    # "n.name is 'p'"
    if (len(condition) == 3 and isinstance(condition[0], str) and
            condition[1] == "is"):
        # n.name means we compare the next letter to condition[2],
        # parse_feat computes the offset given the feature
        offset = parse_feat(condition[0])
        return (lambda word, index: word[index+offset] == condition[2])
    else:
        print(condition)
        raise NotImplementedError("I don't understand the condition: {}".
                                  format(condition))


def parse_feat(feat):
    # n. means next, p. means previous
    offset = 0
    if feat == "name":
        offset = 0
    elif feat == "n.name":
        offset = 1
    elif feat == "n.n.name":
        offset = 2
    elif feat == "n.n.n.name":
        offset = 3
    elif feat == "p.name":
        offset = -1
    elif feat == "p.p.name":
        offset = -2
    elif feat == "p.p.p.name":
        offset = -3
    else:
        raise NotImplementedError("Unknown feature: {}".format(feat))
    return offset


def predict_lex(word, pos=None, lexicon=None, flattened=True):
    """ Predicts the phonetic transcription of word with part of speech `pos`
        using lexicon. If word is not in lexicon returns None.
        `flattened` is a boolean that determines if the prediction should
        be the phones with syllabification or the flattened phones
    """
    if lexicon is None:
        return None
    if flattened:
        heteronym_trans = 2
    else:
        heteronym_trans = 1
    heteronyms = lexicon.get(word, [])
    if len(heteronyms) == 0:
        return None
    elif len(heteronyms) == 1 or pos is None:
        return heteronyms[0][heteronym_trans]
    else:
        # pos->trans
        homograph_dict = dict([(x[0], x[heteronym_trans]) for x in heteronyms])
        if pos in homograph_dict.keys():
            return homograph_dict[pos]
        else:
            return heteronyms[0][heteronym_trans]


def predict_lts(word, lts_lambda, silences=True):
    """
    To predict using Letter To Sound Rules we pad the word with zeros (as done
    in Festival LTS training. Then we choose the right tree for each character
    in our word and predict the phonemes, that are returned in a list.)
    """
    phonemes = []
    word_list = [0, 0, "#"] + list(word) + ["#", 0, 0]
    for word_index in range(3, len(word_list)-3):
        word_char = word_list[word_index]
        if word_char not in lts_lambda.keys():
            logger.warn("Missing letter {} in LTS rules for word {}".format(word_char, word))
            return []
        tree_lambda = lts_lambda[word_char]
        phone = tree_lambda(word_list, word_index)
        phonemes.append(phone)
    if silences:
        return phonemes
    else:
        return [x for x in phonemes if x != "_epsilon_"]


def predict_letters(letters, lts_lambda, silences=True):
    """
    To predict using Letter To Sound Rules we pad the word with zeros (as done
    in Festival LTS training. Then we choose the right tree for each character
    in our word and predict the phonemes, that are returned in a list.)
    """
    phonemes = []
    word_list = [0, 0, '#'] + letters + ["#", 0, 0]
    for word_index in range(3, len(word_list)-3):
        word_char = word_list[word_index]
        tree_lambda = lts_lambda[word_char]
        phone = tree_lambda(word_list, word_index)
        phonemes.append(phone)
    if silences:
        return phonemes
    else:
        return [x for x in phonemes if x != "_epsilon_"]


def predict(word, pos=None, lexicon=None, lts=None):
    """To predict a word we use the lexicon and, as fallback the letter to
    sound rules.
    """
    wordpred = predict_lex(word, pos, lexicon)
    if wordpred is None:
        return predict_lts(word, lts)
    else:
        return wordpred


def phone_normalize(phones):
    output = []
    for phone in phones:
        if phone == "_epsilon_":
            continue
        output.extend(phone.split("-"))
    return output


def test_lts(align, lts, log_file=None):
    """Accuracy of the lts applied to lexicon"""
    count_word_right = 0
    count_word_wrong = 0
    try:
        if log_file is not None:
            log_fh = open(log_file, "w")
        for (i, (letters, pos, phones)) in enumerate(align):
            progress_bar(i, len(align))
            translts = predict_letters(letters, lts, silences=True)
            norm_phones = phone_normalize(phones)
            norm_translts = phone_normalize(translts)
            if all([x == y for (x, y) in zip(norm_phones, norm_translts)]):
                count_word_right += 1
            else:
                if log_file is not None:
                    print("".join(letters), list(zip(norm_phones, norm_translts)), file=log_fh)
                count_word_wrong += 1
    finally:
        if log_file is not None:
            log_fh.close()
    accuracy = count_word_right/(count_word_right + count_word_wrong)
    return accuracy


def prune_lexicon(lexicon, lts):
    """Predicts all the lexicon words with lts rules, keeping in a dictionary
    the words that are not predicted correctly"""
    pruned_lex = defaultdict(list)
    for word, heteronyms in lexicon.items():
        word_lower = word.lower()
        for (pos, syl, trans) in heteronyms:
            translts = predict_lts(word_lower, lts, silences=False)
            if trans != translts or len(heteronyms) > 1:
                pruned_lex[word_lower].append((pos, syl, trans))
    return pruned_lex


def write_syls(syls):
    output = []
    output.append("(")
    for syl in syls:
        output.append("(")
        phones = syl[0]
        output.append("(")
        output.append(" ".join(phones))
        output.append(") ")
        stress = syl[1]
        output.append(str(stress))
        output.append(") ")
    output.append(")")
    return "".join(output)


def write_lex(pruned_lex, filename, flattened=True):
    with open(filename, "w") as fd:
        for word in sorted(pruned_lex.keys()):
            for pos_syls_flattened in pruned_lex[word]:
                (pos, syls, flattened_phones) = pos_syls_flattened
                if flattened:
                    if flattened_phones is None:
                        phones_out = write_syls(syls)
                    else:
                        phones_out = "(" + " ".join(flattened_phones) + " )"
                else:
                    # take syls and convert it to a scheme string
                    raise NotImplementedError("Not needed")
                out = '( "' + word + '" ' + pos + " " + phones_out + ")"
                print(out, file=fd)

