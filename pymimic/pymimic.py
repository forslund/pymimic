from __future__ import absolute_import, division, print_function, \
                       unicode_literals

from ctypes import *
import struct

import os


mimic_lib = None
usenglish_lib = None
cmulex_lib = None

eng = b"eng"
usenglish = b"usenglish"

venv = os.environ.get('VIRTUAL_ENV', '')
lib_paths = ['', venv + '/lib/', venv + '/usr/lib/']

feature_setter = {}

def require_libmimic(func):
    def inner(*args, **kwargs):
        global usenglish_lib
        global cmulex_lib
        global mimic_lib
        global feature_setter

        if mimic_lib is None:
            lib_path = ''
            for p in lib_paths:
                if os.path.isfile(p + '/' + 'libttsmimic.so'):
                    lib_path = p + '/'
                    break
            usenglish_lib = CDLL(lib_path + 'libttsmimic_lang_usenglish.so')
            cmulex_lib = CDLL(lib_path + 'libttsmimic_lang_cmulex.so')
            mimic_lib = CDLL(lib_path + 'libttsmimic.so')

            # declare function return types
            mimic_lib.mimic_text_to_wave.restype = POINTER(_MimicWave)
            mimic_lib.utt_wave.restype = POINTER(_MimicWave)
            mimic_lib.copy_wave.restype = POINTER(_MimicWave)
            mimic_lib.new_utterance.restype = POINTER(_MimicUtterance)
            mimic_lib.mimic_voice_load.restype = POINTER(_MimicVoice)
            mimic_lib.item_feat_float.restype = c_float
            mimic_lib.item_feat_float.argtypes = [c_void_p, c_char_p]
            mimic_lib.item_feat_string.restype = c_char_p
            mimic_lib.item_feat_string.argtypes = [c_void_p, c_char_p]
            mimic_lib.feat_set_float.argtypes = [POINTER(_MimicFeature), c_char_p, c_float]
            mimic_lib.utt_relation.restype = POINTER(_MimicRelation)
            mimic_lib.relation_head.restype = c_void_p
            mimic_lib.relation_head.argtypes = [POINTER(_MimicRelation)]
            mimic_lib.item_next.restype = c_void_p
            mimic_lib.item_next.argtypes = [c_void_p]
            mimic_lib.new_features.restype = POINTER(_MimicFeature)
            feature_setter = {
                float: mimic_lib.feat_set_float,
                str: mimic_lib.feat_set_string,
                int: mimic_lib.feat_set_int
            }

            mimic_lib.mimic_add_lang(eng,
                                     usenglish_lib.usenglish_init,
                                     cmulex_lib.cmulex_init)
            mimic_lib.mimic_add_lang(usenglish,
                                     usenglish_lib.usenglish_init,
                                     cmulex_lib.cmulex_init)
        return func(*args, **kwargs)

    return inner


class _MimicVal(Structure):
    pass


class _MimicFeatValPair(Structure):
    pass


_MimicFeatValPair._fields_ = [
    ('name', c_char_p),
    ('val', POINTER(_MimicVal)),
    ('next', POINTER(_MimicFeatValPair))
    ]


class _MimicFeature(Structure):
    _fields_ = [
        ('head', POINTER(_MimicFeatValPair)),
        ('ctx', c_void_p),
        ('owned_strings', POINTER(_MimicVal))
    ]


class _MimicUtterance(Structure):
    _fields_ = [
        ('features', POINTER(_MimicFeature)),
        ('ffunctions', POINTER(_MimicFeature)),
        ('relations', POINTER(_MimicFeature)),
        ('ctx', c_void_p)
    ]


class _MimicVoice(Structure):
    _fields_ = [
        ('name', c_char_p),
        ('features', POINTER(_MimicFeature)),
        ('ffunctions', POINTER(_MimicFeature))
    ]


class _MimicWave(Structure):
    _fields_ = [
        ('type', c_char_p),
        ('sample_rate', c_int),
        ('num_samples', c_int),
        ('num_channels', c_int),
        ('samples', POINTER(c_short)),
    ]

    def __str__(self):
        sample_list = [self.samples[i] for i in range(self.num_samples)]
        return struct.pack('%sh' % len(sample_list), *sample_list)


class _MimicRelation(Structure):
    _fields_ = [
        ('features', POINTER(_MimicVal)),
        ('utterance', POINTER(_MimicUtterance)),
        ('head', c_void_p),
        ('tail', c_void_p)
    ]

class UtterancePhones():
    @require_libmimic
    def __init__(self, utterance):
        self.u = utterance

    def __iter__(self):
        rel = mimic_lib.utt_relation(self.u, b'Segment')
        if rel != 0:
            self.current = mimic_lib.relation_head(rel)
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        if not self.current:
            raise StopIteration

        string = mimic_lib.item_feat_string(self.current, b'name')
        endtime = mimic_lib.item_feat_float(self.current, b'end')
        self.current = mimic_lib.item_next(self.current)
        return (string, endtime)


class Utterance():
    @require_libmimic
    def __init__(self, text, voice, features=[]):
        self.pointer = mimic_lib.new_utterance()
        mimic_lib.utt_set_input_text(self.pointer, text)
        mimic_lib.utt_init(self.pointer, voice.pointer)
        mimic_lib.utt_synth(self.pointer)
        self.set_features(features)

    def set_features(self, features):
        self.features = mimic_lib.new_features()
        for name, val in features:
            feature_setter[type(val)](self.features, name, val)
        mimic_lib.feat_copy_into(self.features,
                                 self.pointer.contents.features)

    @property
    def features(self):
        return self.pointer.contents.features

    @property
    def phonemes(self):
        u = UtterancePhones(self.pointer)
        return [phone for phone in u]

    def __del__(self):
        mimic_lib.delete_utterance(self.pointer)

class Voice():
    @require_libmimic
    def __init__(self, name, features=[]):
        self.pointer = mimic_lib.mimic_voice_load(name.encode('utf-8'))
        self.name = name
        if self.pointer == 0:
            raise ValueError
        self.set_features(features)

    def set_features(self, features):
        self.features = mimic_lib.new_features()
        for name, val in features:
            feature_setter[type(val)](self.features, name, val)
        mimic_lib.feat_copy_into(self.features,
                                 self.pointer.contents.features)

    @property
    def features(self):
        return self.pointer.contents.features

    def __str__(self):
        return 'Voice: ' + self.name

    def __del__(self):
        mimic_lib.delete_voice(self.pointer)


class Speak():
    @require_libmimic
    def __init__(self, text, voice):
        self.utterance = Utterance(text.encode('utf-8'), voice)
        self.mimic_wave = mimic_lib.utt_wave(self.utterance.pointer)
        self.mimic_wave = mimic_lib.copy_wave(self.mimic_wave)
        self.string = None

    @property
    def phonemes(self):
        return self.utterance.phonemes
    @property
    def sample_rate(self):
        return self.mimic_wave.contents.sample_rate // 2

    @property
    def channels(self):
        return self.mimic_wave.contents.num_channels

    @property
    def sample_size(self):
        return 2

    @property
    def num_samples(self):
        return self.mimic_wave.contents.num_samples

    @property
    def samples(self):
        return self.mimic_wave.contents.samples

    def bin(self):
        if self.string is None:
            samples = cast(self.samples, POINTER(c_char))
            self.string = b""
            for i in range(self.num_samples * self.sample_size):
                self.string = self.string + samples[i]
        return self.string

    def __del__(self):
        mimic_lib.delete_wave(self.mimic_wave)
