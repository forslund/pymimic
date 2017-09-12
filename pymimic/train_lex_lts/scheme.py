##############################################################################
# This interpreter of a subset of the scheme dialect of lisp is based on:
# Lispy: Scheme Interpreter in Python
#
# (c) Peter Norvig, 2010-14; See http://norvig.com/lispy.html
#
# Modifications: (Sergio Oller - github.com/zeehio)
# - The tokenizer uses deque for faster performance
# - atom unquotes string symbols (useful for parsing lexicon in festival
#   format)
##############################################################################

from __future__ import unicode_literals
from __future__ import print_function

from collections import deque

Symbol = str  # A Scheme Symbol is implemented as a Python str
List = list  # A Scheme List is implemented as a Python list
Number = (int, float)  # A Scheme Number is implemented as a int or float
String = str  # A Scheme Symbol that is a string


def tokenize(chars):
    "Convert a string of characters into a list of tokens."
    return deque(chars.replace('(', ' ( ').replace(')', ' ) ').split())


def parse(program, encoding="utf-8"):
    "Read a Scheme expression from a string."
    return read_from_tokens(tokenize(program), encoding)


def read_from_tokens(tokens, encoding):
    "Read an expression from a sequence of tokens."
    if len(tokens) == 0:
        raise SyntaxError('unexpected EOF while reading')
    token = tokens.popleft()
    if token == '(':
        L = []
        while tokens[0] != ')':
            L.append(read_from_tokens(tokens, encoding))
        tokens.popleft()  # pop off ')'
        return L
    elif token == ')':
        raise SyntaxError('unexpected )')
    else:
        return atom(token, encoding)


def atom(token, encoding):
    """Numbers become numbers; Strings become strings,
     every other token is a symbol."""
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            if token[0] == '"' and token[-1] == '"':
                return String(token[1:-1])
            else:
                return Symbol(token)
