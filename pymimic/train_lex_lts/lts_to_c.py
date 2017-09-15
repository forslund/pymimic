# -*- coding: utf-8 -*-
"""
Created on Fri Apr  8 01:18:41 2016

@author: sergio
"""

import os
from subprocess import call, STDOUT
from .utils import progress_bar
from .scheme import parse
from collections import defaultdict

def _call_wfst_build(input_fn, output_fn, wfst_build, logfh=None):
    wfst_build_args = ["-heap", "10000000", "-type", "rg", "-detmin",
                       "-o", output_fn, input_fn]
    if logfh is not None:
        log_stderr = STDOUT
    else:
        log_stderr = None
    call([wfst_build] + wfst_build_args, stdout=logfh, stderr=log_stderr)
    return

def lts_rg_to_wfst(all_letters, rgdir, wfstdir, wfst_build):
    os.makedirs(wfstdir, exist_ok=True)
    for (i, let) in enumerate(all_letters):
        progress_bar(i, len(all_letters))
        input_fn = "{}/{}.tree.rg".format(rgdir, let)
        output_fn = "{}/{}.tree.wfst".format(wfstdir, let)
        with open(os.path.join(wfstdir, let + "_rg_to_wfst.log"), "w") as fh:
            _call_wfst_build(input_fn, output_fn, wfst_build=wfst_build, logfh=fh)

def _lts_drop_probabilities_tree(leaf):
    if not isinstance(leaf, list):
        raise ValueError("Should not happen")
    if len(leaf) == 3 and isinstance(leaf[0][1], str) and leaf[0][1] == "is":
        return [leaf[0], _lts_drop_probabilities_tree(leaf[1]), _lts_drop_probabilities_tree(leaf[2])]
    else:
        return leaf[-1]

def lts_drop_probabilities(lts_rules):
    return [(letter, _lts_drop_probabilities_tree(tree)) for (letter, tree) in lts_rules]

def _is_terminal(leaf):
    return not (isinstance(leaf, list) and len(leaf) == 3 and isinstance(leaf[0][1], str) and leaf[0][1] == "is")

def _lts_to_rg_leaf(leaf, links, num_states, this_node):
    if _is_terminal(leaf):
        if leaf == "_epsilon_":
            leaf = "epsilon"
        links.append(("s" + str(this_node), leaf))
    else:
        true_daughter = num_states + 1
        false_daughter = num_states + 2
        links.append(("s" + str(this_node), "_" + "_".join([str(x) for x in leaf[0]]) + "_", "s" + str(true_daughter)))
        links.append(("s" + str(this_node), "_not_" + "_".join([str(x) for x in leaf[0]]) + "_", "s" + str(false_daughter)))
        num_states += 2
        (links, num_states) = _lts_to_rg_leaf(leaf[1], links, num_states, true_daughter)
        (links, num_states) = _lts_to_rg_leaf(leaf[2], links, num_states, false_daughter)
    return (links, num_states)

def lts_to_rg(lts_rules, rgdir):
    os.makedirs(rgdir, exist_ok=True)
    for (letter, tree) in lts_rules:
        links = _lts_to_rg_leaf(tree, [], 1, 1)[0]
        with open(os.path.join(rgdir, letter + ".tree.rg"), "w") as fh:
            print("(RegularGrammar\n name\n nil\n (", file=fh)
            for link in links:
               if len(link) == 3:
                   print("({} -> \"{}\" {})".format(link[0], link[1], link[2]), file=fh)
               elif len(link) == 2:
                   print("({} -> {})".format(link[0], link[1]), file=fh)
               else:
                   raise ValueError("Should not happen")
            print("))", file=fh)


def lts_to_wfst(lts_rules, rgdir, wfstdir, wfst_build):
    lts_rules = lts_drop_probabilities(lts_rules)
    lts_to_rg(lts_rules, rgdir)
    all_letters = sorted([x[0] for x in lts_rules])
    lts_rg_to_wfst(all_letters, rgdir, wfstdir, wfst_build)


def _write_c_header(headers, lts_prefix):
    output = ["/*******************************************************/",
              "/**  Autogenerated lts rules (regex) for lexicon {}     */".format(lts_prefix),
              "/*******************************************************/",
              ""]
    output += ['#include "{}"'.format(x) for x in headers]
    return output

def lts_feat(trans):
    """ Returns the feature number represented in this transition name."""
    fname = trans[5:-1]
    (feat, str_is, letter) = fname.split("_")
    if feat == "p.p.p.p.name":
        return 0
    elif feat == "p.p.p.name":
        return 1
    elif feat == "p.p.name":
        return 2
    elif feat == "p.name":
        return 3
    elif feat == "n.name":
        return 4
    elif feat == "n.n.name":
        return 5
    elif feat == "n.n.n.name":
        return 6
    elif feat == "n.n.n.n.name":
        return 7
    else:
        raise ValueError("Unknown feat", feat, "in", trans)

def lts_phone(ph, phone_table):
    if ph not in phone_table:
        phone_table.append(ph)
    return (phone_table.index(ph), phone_table)

def lts_val(letter):
    return ord(letter[-2])


def _parse_wfst(wfst_file, state_index, phone_table):
    """Dump the WFST as a byte table to ifd.  Jumps are dumped as
       #define's to ofdh so forward references work.  state_index is the 
       rule position.  Each state is saves as
       feature  value  true_addr  false_addr
       Feature and value are single bytes, which addrs are double bytes.
    """
    output = []
    feats = []
    vals = []
    qtrues = []
    qfalses = []
    state = None
    lines = []
    tree_to_state_map = dict()
    with open(wfst_file) as fh:
        # Skip wfst header
        in_header = True
        for line in fh.readlines():
            if not in_header:
                lines.append(line)
            if line.startswith("EST_Header_End"):
                in_header = False
    wfst_tree = parse("(" + " ".join(lines) + ")")
    for tree in wfst_tree:
        num_tree = tree[0][0]
        final_or_not = tree[0][1]
        num_leafs = tree[0][2]
        tree_to_state_map[num_tree] = state_index
        if final_or_not == "final":
            state_index -= 1
        elif num_leafs > 0 and "_" in tree[1][0]:
            feats.append(lts_feat(tree[1][0]))
            vals.append(lts_val(tree[1][0]))
            qtrues.append(tree[2][2])
            qfalses.append(tree[1][2])
        else:
            (phone_idx, phone_table) = lts_phone(tree[1][0], phone_table)
            feats.append(255)
            vals.append(phone_idx)
            qtrues.append(-1)
            qfalses.append(-1)
        state_index += 1
    for (feat, val, qtrue, qfalse) in zip(feats, vals, qtrues, qfalses):
        if qtrue != -1:
            output.append((feat, val, tree_to_state_map[qtrue], tree_to_state_map[qfalse]))
        else:
            output.append((feat, val, -1, -1))
    return (state_index, phone_table, output)

def _create_c_vec_values(length, positions_values, missing = "0"):
    vec = length*[missing]
    for (position, value) in positions_values:
        vec[position] = str(value)
    return vec

def _rec_dd():
    return defaultdict(_rec_dd)

def _rule_to_struct(state):
    if state[1] > 0x1FFFFF:
        raise ValueError("Value in rule too large: (feat, val, qtrue, qfalse) = ", state)
    if state[0] > 0xFF:
        raise ValueError("Feat in rule too large: (feat, val, qtrue, qfalse) = ", state)
    featval = (state[1] & 0x001FFFFF) | ( (state[0] & 0x000000FF) << 24)
    qtrue = state[2]
    qfalse = state[3]
    return "{" + "{}, {}, {}".format(featval, qtrue, qfalse) + "}"

def _extract_info_from_wfst(all_letters, wfstdir):
    phone_table = ["epsilon"]
    # Extract info from wfst files:
    rule_index = dict()
    start_index = 0
    models = []
    for i, letter in enumerate(all_letters):
        progress_bar(i, len(all_letters))
        wfst_file = os.path.join(wfstdir, letter + ".tree.wfst")
        rule_index[letter] = start_index
        (start_index, phone_table, model) = _parse_wfst(wfst_file, start_index, phone_table)
        models += model
    return (models, rule_index, phone_table)

def convert_states_to_rules(models, lts_prefix):
    model_rules_c = []
    # Write the rules: (the +1 rule is for the zero at the end)
    model_rules_c.append("const cst_lts_rule {}_lts_model[{}] = ".format(lts_prefix, len(models) + 1))
    model_rules_c.append("{")
    all_rules = [_rule_to_struct(x) for x in models]
    rules_c_code = "  " + ",\n  ".join(all_rules)
    # For the last zeros at the end:
    rules_c_code += ","
    model_rules_c.append(rules_c_code)
    # Append a zero at the end (maybe not needed?)
    model_rules_c.append("  {0, 0, 0}")
    model_rules_c.append("};")
    model_rules_c.append("")
    return model_rules_c

def _create_c_vec(vartype, varname, varlength, positions_values, missing):
    values = ", ".join(_create_c_vec_values(varlength, positions_values, missing = missing))
    return vartype + " " + varname + "[" + str(varlength) + "] = {" + values + "};"

def create_letter_index_map(all_letters, rule_index, lts_prefix):
    # The letter_table (bytes to start indices)
    letter_idx_c = []
    letters_by_bytes = [_rec_dd(), _rec_dd(), _rec_dd(), _rec_dd()]
    for let_idx, let in enumerate(all_letters):
        lab = [x for x in let.encode("utf-8")]
        if len(lab) == 1:
            letters_by_bytes[0][lab[0]] = rule_index[let]
        elif len(lab) == 2:
            letters_by_bytes[1][lab[0]-192][lab[1]-128] = rule_index[let]
        elif len(lab) == 3:
            letters_by_bytes[2][lab[0]-224][lab[1]-128][lab[2]-128] = rule_index[let]
        elif len(lab) == 4:
            letters_by_bytes[3][lab[0]-240][lab[1]-128][lab[2]-128][lab[3]-128] = rule_index[let]
    vecdef = "{}_lts_letter_index_v".format(lts_prefix)
    MAP_UNICODE_TO_INT_NOT_FOUND = "-1"
    FREEABLE = "0"
    map_unicode_to_int_fields = ["NULL", "NULL", "NULL", "NULL", MAP_UNICODE_TO_INT_NOT_FOUND, FREEABLE]
    for i, letters_of_n_bytes in enumerate(letters_by_bytes):
        if len(letters_of_n_bytes) > 0:
            if i == 0:
                vec_name = vecdef + str(i+1)
                letter_idx_c.append(_create_c_vec("const int32_t",
                                                  vec_name,
                                                  128,
                                                  letters_of_n_bytes.items(),
                                                  missing = "0"))
                map_unicode_to_int_fields[0] = "(int32_t *) " + vec_name
            elif i == 1:
                for (key1, nested_dict1) in letters_of_n_bytes.items():
                    vec_name = vecdef + str(i+1) + "_" + str(key1)
                    letter_idx_c.append(_create_c_vec("const int32_t",
                                                      vec_name,
                                                      64,
                                                      nested_dict1.items(),
                                                      missing = "0"))
                    letters_of_n_bytes[key1] = vec_name
                vec_name = vecdef + str(i+1)
                letter_idx_c.append(_create_c_vec("const int32_t *",
                                                  vec_name,
                                                  32,
                                                  letters_of_n_bytes.items(),
                                                  missing = "NULL"))
                map_unicode_to_int_fields[i] = "(int32_t **) " + vec_name
            elif i == 2:
                for (key1, nested_dict1) in letters_of_n_bytes.items():
                    for (key2, nested_dict2) in nested_dict1.items():
                        vec_name = vecdef + str(i+1) + "_" + str(key1) + "_" + str(key2)
                        letter_idx_c.append(_create_c_vec("const int32_t",
                                                          vec_name,
                                                          64,
                                                          nested_dict2.items(),
                                                          missing = "0"))
                        nested_dict1[key2] = vec_name
                    vec_name = vecdef + str(i+1) + "_" + str(key1)
                    letter_idx_c.append(_create_c_vec("const int32_t *",
                                                      vec_name,
                                                      64,
                                                      nested_dict1.items(),
                                                      missing = "NULL"))
                    letters_of_n_bytes[key1] = vec_name
                vec_name = vecdef + str(i+1)
                letter_idx_c.append(_create_c_vec("const int32_t **",
                                                  vec_name,
                                                  16,
                                                  letters_of_n_bytes.items(),
                                                  missing = "NULL"))
                map_unicode_to_int_fields[i] = "(int32_t ***) " + vec_name
            elif i == 3:
                for (key1, nested_dict1) in letters_of_n_bytes.items():
                    for (key2, nested_dict2) in nested_dict1.items():
                        for (key3, nested_dict3) in nested_dict2.items():
                            vec_name = vecdef + str(i+1) + "_" + str(key1) + "_" + str(key2) + "_" + str(key3)
                            letter_idx_c.append(_create_c_vec("const int32_t",
                                                              vec_name,
                                                              64,
                                                              nested_dict3.items(),
                                                              missing = "0"))
                            nested_dict2[key3] = vec_name
                        vec_name = vecdef + str(i+1) + "_" + str(key1) + "_" + str(key2)
                        letter_idx_c.append(_create_c_vec("const int32_t *",
                                                          vec_name,
                                                          64,
                                                          nested_dict2.items(),
                                                          missing = "NULL"))
                        nested_dict1[key2] = vec_name
                    vec_name = vecdef + str(i+1) + "_" + str(key1)
                    letter_idx_c.append(_create_c_vec("const int32_t **",
                                                      vec_name,
                                                      64,
                                                      nested_dict1.items(),
                                                      missing = "NULL"))
                    letters_of_n_bytes[key1] = vec_name
                vec_name = vecdef + str(i+1)
                letter_idx_c.append(_create_c_vec("const int32_t ***",
                                                  vec_name,
                                                  8,
                                                  letters_of_n_bytes.items(),
                                                  missing = "NULL"))
                map_unicode_to_int_fields[i] = "(int32_t ****) " + vec_name
    letter_idx_c.append("")
    letter_idx_c.append("const map_unicode_to_int {}_lts_letter_index = ".format(lts_prefix) + "{")
    letter_idx_c.append(", ".join(map_unicode_to_int_fields) + "};")
    return letter_idx_c

def create_phone_table(phone_table, lts_prefix):
    # The phone table (terminal rule values are integer values that map to these phones)
    phone_table_c = []
    phone_table_c.append("")
    phone_table_c.append("const char * const {}_lts_phone_table[{}] = ".format(lts_prefix, len(phone_table) + 1))
    phone_table_c.append("{")
    for p in phone_table:
        phone_table_c.append('    "{}",'.format(p))
    phone_table_c.append("    NULL")
    phone_table_c.append("};")
    return phone_table_c

def lts_regex_to_c(lts_prefix, all_letters, wfstdir, c_dir):
    """Converts the LTS rules for the letters in all letters to a C compilation structure for mimic.
       It uses the WFST trees to generate the C source code and headers
    """

    (models, rule_index, phone_table) = _extract_info_from_wfst(all_letters, wfstdir)

    # Convert rules to C structures:
    model_rules_c = convert_states_to_rules(models, lts_prefix)
    phone_table_c = create_phone_table(phone_table, lts_prefix)
    letter_idx_c = create_letter_index_map(all_letters, rule_index, lts_prefix)

   # Write C headers for each generated file:
    lts_rules_c = (
        _write_c_header(["cst_string.h", "cst_lts.h", "cst_lexicon.h"], lts_prefix))
    lts_model_c = (
        _write_c_header(["cst_string.h", "cst_lts.h", "cst_lexicon.h"], lts_prefix))

    lts_rules_c += model_rules_c
    lts_rules_c += phone_table_c
    lts_rules_c += letter_idx_c

    os.makedirs(c_dir, exist_ok=True)
    with open(os.path.join(c_dir, lts_prefix + "_lts_rules.c"), "w") as fd:
        fd.write("\n".join(lts_rules_c) + "\n")

def lts_to_c(name, lts_rules, rgdir, wfstdir, wfst_build, c_dir):
    lts_to_wfst(lts_rules, rgdir, wfstdir, wfst_build)
    all_letters = sorted([x[0] for x in lts_rules])
    lts_regex_to_c(name, all_letters, wfstdir, c_dir)

