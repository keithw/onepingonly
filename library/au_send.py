import pyaudio
import sys
import struct
import math
import StringIO
import scipy.signal

from au_defs import *

TIME = 0 # seconds

cachelen = SAMPLES_PER_SECOND
COS_CACHE = [0] * cachelen
SIN_CACHE = [0] * cachelen
for i in range( cachelen ):
    COS_CACHE[ i ] = math.cos( CARRIER_CYCLES_PER_SECOND * TIME * 2 * math.pi )
    SIN_CACHE[ i ] = math.sin( CARRIER_CYCLES_PER_SECOND * TIME * 2 * math.pi )
    TIME += 1.0 / SAMPLES_PER_SECOND

total_sample_count = 0

nyquist_freq = float(SAMPLES_PER_SECOND) / 2.0
passband = float(CARRIER_CYCLES_PER_SECOND) / nyquist_freq

filter_numer, filter_denom = scipy.signal.iirdesign( passband * 0.75 * 0.975, passband * 0.75 * 1.025, 1, 60 )
filter_state = scipy.signal.lfiltic( filter_numer, filter_denom, [] )

def send( samples, stream, samples_per_chunk ):
    return raw_send( modulate( samples, samples_per_chunk ), stream )

def expand( samples, factor ):
    out = []
    for s in samples:
        for i in range( factor ):
            out.append( s )
    return out

def raw_send( chunks, stream ):
    for chunk in chunks:
        stream.write( chunk )

# Send one chunk of I samples, modulated onto the carrier frequency
def modulate( samples, samples_per_chunk ):
    global TIME
    global total_sample_count
    global filter_state

    sample_count = 0
    chunk_data = [ "" ]
    chunk_number = 0

    # Write payload

    samples, filter_state = scipy.signal.lfilter( filter_numer, filter_denom, samples, zi=filter_state )
    
    for s in samples:
        chunk_data[ chunk_number ] += struct.pack( 'f', ((s * AMPLITUDE) + DC) * COS_CACHE[ total_sample_count % cachelen ] )
        total_sample_count += 1
        sample_count += 1

        if sample_count == samples_per_chunk:
            chunk_number += 1
            chunk_data.append( "" )
            sample_count = 0

    return chunk_data
