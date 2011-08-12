#!/usr/bin/python

import pyaudio
import sys
import struct
import math

FORMAT = pyaudio.paFloat32
CHANNELS = 1
SAMPLE_RATE = 48000
FREQ = 4000
CYCLES_PER_BIT = 8
BIT = int(SAMPLE_RATE*CYCLES_PER_BIT/FREQ)
CHUNK = int(16 * BIT)

p = pyaudio.PyAudio()

stream = p.open(format = FORMAT,
                channels = CHANNELS,
                rate = SAMPLE_RATE,
                input = False,
                output = True,
                frames_per_buffer = CHUNK)

TIME = 0 # seconds

while True:
    chunkdata = ""
    # make every bit
    bitcount = 0
    sign = 1
    while bitcount < CHUNK/BIT:
        bitdata = ""
        framecount = 0
        while framecount < BIT:
            value = sign * .01 * math.cos( FREQ * TIME * (2 * math.pi) )
            bitdata += struct.pack( 'f', value )
            TIME += 1.0 / SAMPLE_RATE
            framecount += 1
        chunkdata += bitdata
        sign = -sign
        bitcount += 1
#    print "Wrote %d bits" % bitcount

    stream.write(chunkdata)

stream.stop_stream()
stream.close()
p.terminate()
