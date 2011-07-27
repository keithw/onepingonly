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
                input = False,
                output = True,
                frames_per_buffer = CHUNK)

TIME = 0 # seconds
data = ""

while True:
    data = ""
    while len(data) < CHUNK:
        value = .25 * math.sin( 480.0 * TIME * (2 * math.pi) )
        data += struct.pack( 'f', value )
        TIME += 1.0 / RATE

    stream.write(data)

stream.stop_stream()
stream.close()
p.terminate()
