from ctypes import *
import struct
from os.path import dirname, abspath


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


mimic_lib = CDLL(dirname(abspath(__file__)) + '/libpymimic.so')
mimic_lib.mimic_text_to_wave.restype = POINTER(_MimicWave)

mimic_lib.mimic_add_lang("eng",
                         mimic_lib.usenglish_init,
                         mimic_lib.cmulex_init)
mimic_lib.mimic_add_lang("usenglish",
                         mimic_lib.usenglish_init,
                         mimic_lib.cmulex_init)


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
