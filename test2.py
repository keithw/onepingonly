#!/usr/bin/python

import pyaudio
import sys
import struct
import math

FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 44100
CHUNK = 1024

p = pyaudio.PyAudio()

stream = p.open(format = FORMAT,
                channels = CHANNELS,
                rate = RATE,
                input = True,
                output = False,
                frames_per_buffer = CHUNK)


TIME = 0 # seconds
data = ""

while True:
    data = stream.read(CHUNK)
    t = struct.unpack("f"*CHUNK, data)
    print min(t), max(t)

stream.stop_stream()
stream.close()
p.terminate()
