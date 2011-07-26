#!/usr/bin/python

import pyaudio
import sys
import struct
import math

FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 44100
CHUNK = 4410

p = pyaudio.PyAudio()

stream = p.open(format = FORMAT,
                channels = CHANNELS,
                rate = RATE,
                input = True,
                output = False,
                frames_per_buffer = CHUNK)

TIME = 0 # seconds
data = ""
sines = ""
cosines = ""
ctr = 0
while ctr < CHUNK:
    sine_value = math.sin( 440.0 * TIME * (2 * math.pi) )
    sines += struct.pack( 'f', sine_value )
    cosine_value = math.cos( 440.0 * TIME * (2 * math.pi) )
    cosines += struct.pack( 'f', cosine_value )
    TIME += 1.0 / RATE
    ctr += 1

while True:
    data = stream.read(CHUNK)
    t = struct.unpack("f"*CHUNK, data)
    s = struct.unpack("f"*CHUNK, sines)
    c = struct.unpack("f"*CHUNK, cosines)
    magnitude = 0.0
    for i in range(len(t)):
        val, sine_val, cos_val = t[i], s[i], c[i]
        magnitude += math.sqrt(abs(val*sine_val + val*cos_val))
    magnitude /= len(t)
    print magnitude

stream.stop_stream()
stream.close()
p.terminate()
