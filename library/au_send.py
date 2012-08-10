import pyaudio
import sys
import struct
import math
import StringIO
import scipy.signal
import wave
import numpy
import random
import array

from au_filter import Filter
from au_defs import *

total_sample_count = 0

lowpass = Filter( 0, 500 ) # hardcoded bandwidth

def send( samples, stream, samples_per_chunk, carrier_freq ):
    return raw_send( modulate_float( samples, carrier_freq,
                                     samples_per_chunk ),
                     stream )

def expand( samples, factor ):
    out = []
    for s in samples:
        for i in range( factor ):
            if i == 0:
                out.append( s )
            else:
                out.append( 0 )
    return out

def raw_send( chunks, stream ):
    for chunk in chunks:
        stream.write( chunk )

# Send one chunk of I samples, modulated onto the carrier frequency
def modulate_float( samples, carrier_freq, samples_per_chunk ):
    global total_sample_count
    global lowpass

    sample_count = 0
    chunk_data = [ "" ]
    chunk_number = 0

    # Write payload

    samples = lowpass( samples )
    
    for s in samples:
        chunk_data[ chunk_number ] += struct.pack( 'f', ((s * AMPLITUDE) + DC) * math.cos( total_sample_count * 2 * math.pi * carrier_freq / SAMPLES_PER_SECOND ) )
        total_sample_count += 1
        sample_count += 1

        if sample_count == samples_per_chunk:
            chunk_number += 1
            chunk_data.append( "" )
            sample_count = 0

    return chunk_data

def modulate_frame( samples, carrier_freq, existing=None ):
    delay = random.randint( 0, SAMPLES_PER_SECOND )

    samples = numpy.hstack( (-1 * numpy.ones( delay ), samples) )

    if existing != None:
        if len(samples) > len(existing):
            existing = numpy.hstack( (existing, numpy.zeros( len(samples) - len(existing) )) )
        if len(existing) > len(samples):
            samples = numpy.hstack( (samples, numpy.zeros( len(existing) - len(samples) )) )
    else:
        existing = numpy.zeros( len(samples) )

    assert( len(existing) == len(samples) )

    args = numpy.arange( 0, len(samples) ) * carrier_freq * 2 * math.pi / SAMPLES_PER_SECOND
    existing += numpy.cos(args) * (lowpass( samples ) * AMPLITUDE + DC)

    return existing

def write_wav( filename, samples ):
    wave_file = wave.open( filename, "w" )

    wave_file.setparams( (1, 2, 8000, 0, "NONE", "NONE") )

    wave_file.writeframes( array.array( 'h', [ int(4096.0*x) for x in samples ] ).tostring() )

    wave_file.close()
