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


def require_libmimic(func):
    def inner(*args, **kwargs):
        global usenglish_lib
        global cmulex_lib
        global mimic_lib

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
            mimic_lib.new_utterance.restype = POINTER(_MimicUtterence)

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


class _MimicUtterence(Structure):
    _fields_ = [
        ('features', POINTER(_MimicFeature)),
        ('ffunctions', POINTER(_MimicFeature)),
        ('relations', POINTER(_MimicFeature)),
        ('ctx', c_void_p)
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


class Utterance():
    @require_libmimic
    def __init__(self, text, voice):
        self.pointer = mimic_lib.new_utterance()
        mimic_lib.utt_set_input_text(self.pointer, text)
        mimic_lib.utt_init(self.pointer, voice.pointer)
        mimic_lib.utt_synth(self.pointer)

    def info(self):
        return

    def __del__(self):
        mimic_lib.delete_utterance(self.pointer)


class Voice():
    @require_libmimic
    def __init__(self, name):
        self.pointer = mimic_lib.mimic_voice_load(name.encode('utf-8'))
        self.name = name
        if self.pointer == 0:
            raise ValueError

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
