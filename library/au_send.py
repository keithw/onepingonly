import pyaudio
import sys
import struct
import math
import StringIO

from au_defs import *

# Open audio channel (input and output)
p = pyaudio.PyAudio()
stream = p.open(format = FORMAT,
                channels = CHANNELS,
                rate = SAMPLES_PER_SECOND,
                input = False,
                output = True,
                frames_per_buffer = SAMPLES_PER_CHUNK)

TIME = 0 # seconds

COS_CACHE = [0] * SAMPLES_PER_SECOND
SIN_CACHE = [0] * SAMPLES_PER_SECOND
for i in range( SAMPLES_PER_SECOND ):
    COS_CACHE[ i ] = math.cos( CARRIER_CYCLES_PER_SECOND * TIME * 2 * math.pi )
    SIN_CACHE[ i ] = math.sin( CARRIER_CYCLES_PER_SECOND * TIME * 2 * math.pi )
    TIME += 1.0 / SAMPLES_PER_SECOND

total_sample_count = 0

# Send one chunk of I samples, modulated onto the carrier frequency
def send( samples ):
    global TIME
    global total_sample_count

    sample_count = 0
    chunk_data = [ "" ]
    chunk_number = 0

    # Write payload
    
    for s in samples:
        chunk_data[ chunk_number ] += struct.pack( 'f', ((s * AMPLITUDE) + DC) * COS_CACHE[ total_sample_count % SAMPLES_PER_SECOND ] )
        total_sample_count += 1
        sample_count += 1

        if sample_count == SAMPLES_PER_CHUNK:
            chunk_number += 1
            chunk_data.append( "" )
            sample_count = 0

    for chunk in chunk_data:
        stream.write( chunk )
