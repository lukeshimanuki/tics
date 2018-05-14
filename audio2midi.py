import os
import numpy as np
import scipy as sp
import scipy.signal as signal
import scipy.fftpack as fft
import scipy.io as io
import scipy.io.wavfile
import matplotlib.pyplot as plt
import rtmidi
from rtmidi import midiconstants
import pyaudio

midiout = rtmidi.MidiOut()
midiout.open_virtual_port('TICS-MIDI')

# Define concert A.
A4_freq = 440
A4_midi = 69
freqs = np.zeros(128, dtype=int)
for i in range(0, 128):
    freqs[i] = round(A4_freq * (2**((i - A4_midi)/12)))

def get_pitch_strengths(fft_data):
    # Try to compensate for rounding the frequencies to ints by including their neighbors.
    return np.abs(fft_data)[freqs-1] + np.abs(fft_data)[freqs] + np.abs(fft_data)[freqs+1]

window_size = 22050
window = signal.hanning(window_size)

pa = pyaudio.PyAudio()

sample_rate = 44100
stream = pa.open(format = pyaudio.paInt16,
                 channels = 1,
                 rate = sample_rate,
                 input = True,
                 output = False,
                 frames_per_buffer = 1024)

data = np.zeros(22050)
last_value = None
i = 0
while stream.is_active():
    raw = stream.read(1024)
    buffer = np.copy(np.frombuffer(raw, dtype=np.int16))
    data[:-1024] = data[1024:]
    data[-1024:] = buffer

    i += 1
    if i >= 10:
        i = 0
    else:
        continue
    out = fft.rfft(window * data)
    out[np.arange(0,80)] = 0
    pitch_strengths = get_pitch_strengths(out)
    value = np.argmax(pitch_strengths)
    if pitch_strengths[value] < 20000:
        value = 0
    if value != last_value:
        onset = i / sample_rate
        if last_value:
            midiout.send_message([midiconstants.NOTE_OFF, last_value, 127])
        if pitch_strengths[value] < 10000000:
            value = 0
        if value:
            midiout.send_message([midiconstants.NOTE_ON, value, 127])
            print(value, pitch_strengths[value], onset)
        last_value = value

stream.close()
