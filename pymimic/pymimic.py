from ctypes import *
import struct

import os

venv = os.environ.get('VIRTUAL_ENV', None)
if venv:
    for p in [venv + '/lib/', venv + '/usr/lib/']:
        if os.path.isfile(p + 'libmimic.so'):
            lib_path = p
            break

usenglish_lib = CDLL(lib_path + 'libmimic_lang_usenglish.so')
cmulex_lib = CDLL(lib_path + 'libmimic_lang_cmulex.so')
mimic_lib = CDLL(lib_path + 'libmimic.so')

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

mimic_lib.mimic_text_to_wave.restype = POINTER(_MimicWave)
eng = "eng"
mimic_lib.mimic_add_lang(eng,
                         usenglish_lib.usenglish_init,
                         cmulex_lib.cmulex_init)
usenglish = "usenglish"
mimic_lib.mimic_add_lang(usenglish,
                         usenglish_lib.usenglish_init,
                         cmulex_lib.cmulex_init)


class Voice():
    def __init__(self, name):
        self.pointer =  mimic_lib.mimic_voice_select(name)
        self.name = name
        if self.pointer == 0:
            raise ValueError

    def __str__(self):
        return 'Voice: ' + self.name

    def __del__(self):
        mimic_lib.delete_voice(self.pointer)


class Speak():
    def __init__(self, text, voice):
        self.mimic_wave = mimic_lib.mimic_text_to_wave(text, voice.pointer)
        self.string = None

    @property
    def sample_rate(self):
        return self.mimic_wave.contents.sample_rate / 2

    @property
    def channels(self):
        return self.mimic_wave.contents.num_channels

    @property
    def sample_size(self):
        return 2

    def __str__(self):
        if self.string is None:
            self.string = str(self.mimic_wave.contents)
        return self.string

    def __del__(self):
        mimic_lib.delete_wave(self.mimic_wave)
