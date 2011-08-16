import pyaudio
import sys
import struct
import math
import StringIO

from au_defs import *

SAMPLES_PER_CHUNK = 32

# Open audio channel (input and output)
p = pyaudio.PyAudio()
stream = p.open(format = FORMAT,
                channels = CHANNELS,
                rate = SAMPLES_PER_SECOND,
                input = True,
                output = False,
                frames_per_buffer = SAMPLES_PER_CHUNK)

TIME = 0 # seconds

assert( abs( (float(SAMPLES_PER_SECOND) / float(CARRIER_CYCLES_PER_SECOND)) - (SAMPLES_PER_SECOND // CARRIER_CYCLES_PER_SECOND) ) < 0.01 )

COS_CACHE = [0] * SAMPLES_PER_SECOND
SIN_CACHE = [0] * SAMPLES_PER_SECOND
for i in range( SAMPLES_PER_SECOND ):
    COS_CACHE[ i ] = math.cos( CARRIER_CYCLES_PER_SECOND * TIME * 2 * math.pi )
    SIN_CACHE[ i ] = math.sin( CARRIER_CYCLES_PER_SECOND * TIME * 2 * math.pi )
    TIME += 1.0 / SAMPLES_PER_SECOND

total_sample_count = 0

num_amplitudes = 512
average_amplitudes = [ 1 ] * num_amplitudes
amplitude_sum = sum( average_amplitudes )

def receive( num_samples ):
    global TIME
    global total_sample_count
    global average_amplitudes
    global amplitude_sum

    sample_count = 0
    samples = []
    while sample_count < num_samples:
        samples.extend( struct.unpack( 'f' * SAMPLES_PER_CHUNK,
                                       stream.read( SAMPLES_PER_CHUNK ) ) )
        sample_count += SAMPLES_PER_CHUNK

    # Demodulate carrier
    demodulated_samples = [0] * sample_count

    imag = complex( 0, 1 )

    # Shift the modulated waveform back down to baseband
    i = 0
    for s in samples:
        I = s * COS_CACHE[ total_sample_count % SAMPLES_PER_SECOND ]
        Q = s * SIN_CACHE[ total_sample_count % SAMPLES_PER_SECOND ]
        demodulated_samples[ i ] = complex( I, Q )
        total_sample_count += 1
        i += 1

    # calculate average amplitude (DC amplitude)
    # we will use this for auto-gain control
    average_amplitude = sum( demodulated_samples ) / float(sample_count)
    average_amplitudes.pop( 0 )
    average_amplitudes.append( average_amplitude )
    amplitude_sum += average_amplitude - average_amplitudes[ 0 ]
    amplitude_overall_average = amplitude_sum / num_amplitudes

    # Shift samples in time back to original phase and amplitude (using carrier)
    shifted_samples = [ y.real for y in [ .5 * (x / amplitude_overall_average - 1) for x in demodulated_samples ] ]

    # Low-pass filter
    window = SAMPLES_PER_SECOND // CARRIER_CYCLES_PER_SECOND
    last_samples = [0] * window
    filtered_samples = [0] * sample_count
    running_sum = sum( last_samples )
    i = 0
    for s in shifted_samples:
        last_samples.pop( 0 )
        last_samples.append( s )
        running_sum += s - last_samples[ 0 ]
        filtered_samples[ i ] = running_sum / window
        i += 1

    return filtered_samples
    
