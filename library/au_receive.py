import pyaudio
import sys
import struct
import math
import StringIO

from au_defs import *

TIME = 0 # seconds

assert( abs( (float(SAMPLES_PER_SECOND) / float(CARRIER_CYCLES_PER_SECOND)) - (SAMPLES_PER_SECOND // CARRIER_CYCLES_PER_SECOND) ) < 0.01 )

cachelen = SAMPLES_PER_SECOND
COS_CACHE = [0] * cachelen
SIN_CACHE = [0] * cachelen
for i in range( cachelen ):
    COS_CACHE[ i ] = math.cos( CARRIER_CYCLES_PER_SECOND * TIME * 2 * math.pi )
    SIN_CACHE[ i ] = math.sin( CARRIER_CYCLES_PER_SECOND * TIME * 2 * math.pi )
    TIME += 1.0 / SAMPLES_PER_SECOND

total_sample_count = 0

num_amplitudes = 8192
amplitudes = [ 1 ]
samples_in_amplitude_history = 0
amplitude_sum = sum( amplitudes )

def receive( num_samples, stream, samples_per_chunk ):
    return demodulate( raw_receive( num_samples, stream, samples_per_chunk ) )

def decimate( samples, factor ):
    out = []
    while len(samples) > 0:
        this_level = samples[0:factor]
        del samples[0:factor]
        assert( len(this_level) == factor or len(samples) == 0 )
        out.append( sum( this_level ) / factor )
    return out

def raw_receive( num_samples, stream, samples_per_chunk ):
    sample_count = 0
    samples = []
    while sample_count < num_samples:
        samples.extend( struct.unpack( 'f' * samples_per_chunk,
                                       stream.read( samples_per_chunk ) ) )
        sample_count += samples_per_chunk
    return samples

def demodulate( samples ):
    global TIME
    global total_sample_count
    global amplitudes
    global amplitude_sum
    global samples_in_amplitude_history

    # Demodulate carrier
    sample_count = len( samples )
    demodulated_samples = [0] * sample_count

    imag = complex( 0, 1 )

    # Shift the modulated waveform back down to baseband
    i = 0
    for s in samples:
        I = s * COS_CACHE[ total_sample_count % cachelen ]
        Q = s * SIN_CACHE[ total_sample_count % cachelen ]
        demodulated_samples[ i ] = complex( I, Q )
        total_sample_count += 1
        i += 1

    if samples_in_amplitude_history == 0: # initializing
        samples_in_amplitude_history = sample_count # we assume same value each call

    # calculate average amplitude (DC amplitude)
    # we will use this for auto-gain control
    total_amplitude = sum( demodulated_samples )
    amplitudes.append( total_amplitude )
    amplitude_sum += total_amplitude
    samples_in_amplitude_history += sample_count

    if samples_in_amplitude_history >= num_amplitudes:
        amplitude_sum -= amplitudes[ 0 ]
        amplitudes.pop( 0 )
        samples_in_amplitude_history -= sample_count

    amplitude_overall_average = amplitude_sum / samples_in_amplitude_history

    # Shift samples in time back to original phase and amplitude (using carrier)
    shifted_samples = [ y.real for y in [ (DC/AMPLITUDE) * (x / amplitude_overall_average - 1) for x in demodulated_samples ] ]

    # Low-pass filter
    window = SAMPLES_PER_SECOND // CARRIER_CYCLES_PER_SECOND
    last_samples = [0] * window
    filtered_samples = [0] * sample_count
    running_sum = sum( last_samples )
    i = 0
    for s in shifted_samples:
        last_samples.append( s )
        running_sum += s - last_samples[ 0 ]
        last_samples.pop( 0 )
        filtered_samples[ i ] = running_sum / window
        i += 1

    return filtered_samples
    
