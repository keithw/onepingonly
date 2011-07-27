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

while True:
    cosines = []
    sines = []
    for i in range(CHUNK):
        cosines.append( math.cos( 440.0 * TIME * (2 * math.pi) ) )
        sines.append( math.sin( 440.0 * TIME * (2 * math.pi) ) )
        TIME += 1.0 / RATE

    # Listen for a tenth of a second
    received_signal = struct.unpack("f"*CHUNK, stream.read(CHUNK))

    sine_amplitude = 0.0
    cosine_amplitude = 0.0
    for i in range(len(received_signal)):
        cosine_amplitude += received_signal[ i ] * cosines[ i ] / len( received_signal )
        sine_amplitude += received_signal[ i ] * sines[ i ] / len( received_signal )

    mag = math.sqrt( cosine_amplitude**2 + sine_amplitude**2 )
    theta = math.atan2( cosine_amplitude, sine_amplitude )

    print mag, theta

stream.stop_stream()
stream.close()
p.terminate()
