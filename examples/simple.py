from pyaudio import PyAudio
from pymimic import *

if __name__ == '__main__':

    v = mimic_lib.mimic_voice_select('../mimic/voices/cmu_us_rms.flitevox')
    s = Speak('Hello there! This is python!', v)

    p = PyAudio()
    stream = p.open(format=2, channels=s.channels,
                    rate=s.sample_rate, output=True)
    stream.write(str(s))
