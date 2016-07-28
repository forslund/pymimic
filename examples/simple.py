from pyaudio import PyAudio
from pymimic import *

from os.path import realpath, dirname

voice_path = dirname(realpath(__file__)) + '/cmu_us_rms.flitevox'
if __name__ == '__main__':

    v = Voice(voice_path)
    s = Speak('Hello there! This is python!', v)

    p = PyAudio()
    stream = p.open(format=2, channels=s.channels,
                    rate=s.sample_rate, output=True)
    stream.write(str(s))
