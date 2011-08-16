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

# Send one chunk of I samples, modulated onto the carrier frequency
def send( samples ):
    global TIME
    assert( len(samples) <= SAMPLES_PER_OUTPUT_PACKET )

    # Fill out samples to length of chunk
    while len(samples) < SAMPLES_PER_OUTPUT_PACKET:
        samples.append( 0 )

    sample_count = 0
    chunk_data = [ "" ]
    chunk_number = 0

    # Write payload
    
    for s in samples:
        chunk_data[ chunk_number ] += struct.pack( 'f', ((s * AMPLITUDE) + DC) * math.cos( CARRIER_CYCLES_PER_SECOND * TIME * 2 * math.pi ) )
        TIME += 1.0 / SAMPLES_PER_SECOND
        sample_count += 1

        if sample_count == SAMPLES_PER_OUTPUT_PACKET:
            chunk_number += 1
            chunk_data.append( "" )
            sample_count = 0

    for chunk in chunk_data:
        stream.write( chunk )
