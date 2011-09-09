import pyaudio
import sys
import struct
import math
import StringIO
import numpy
import scipy.signal

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

num_amplitudes = 32768
amplitudes = [ 1 ]
samples_in_amplitude_history = 0
amplitude_sum = sum( amplitudes )

nyquist_freq = float(SAMPLES_PER_SECOND) / 2.0

passband = float(CARRIER_CYCLES_PER_SECOND) / nyquist_freq

tuner_numer, tuner_denom = scipy.signal.iirdesign( [ passband * 0.8 * 1.025, passband * 1.2 * 0.975 ],
                                                   [ passband * 0.8 * 0.975, passband * 1.2 * 1.025 ],
                                                   1, 60 )
tuner_state = scipy.signal.lfiltic( tuner_numer, tuner_denom, [] )

filter_numer, filter_denom = scipy.signal.iirdesign( passband * 0.975, passband * 1.025, 1, 60 )
filter_state = scipy.signal.lfiltic( filter_numer, filter_denom, [] )

def receive( num_samples, stream, samples_per_chunk ):
    return demodulate( raw_receive( num_samples, stream, samples_per_chunk ) )

def raw_receive( num_samples, stream, samples_per_chunk ):
    sample_count = 0
    samples = []
    while sample_count < num_samples:
        try:
            samples.extend( struct.unpack( 'f' * samples_per_chunk,
                                           stream.read( samples_per_chunk ) ) )
            sample_count += samples_per_chunk
        except IOError:
            sys.stderr.write( "IOError\n" )
            pass

    assert( sample_count == num_samples )
    return samples

def demodulate( samples ):
    global TIME
    global total_sample_count
    global amplitudes
    global amplitude_sum
    global samples_in_amplitude_history

    global tuner_state
    global filter_state

    # Tune in band around carrier frequency
    samples, tuner_state = scipy.signal.lfilter( tuner_numer, tuner_denom, samples, zi=tuner_state )

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
    # we will use this for auto gain control
    total_amplitude = sum( demodulated_samples )
    amplitudes.append( total_amplitude )
    amplitude_sum += total_amplitude
    samples_in_amplitude_history += sample_count

    if samples_in_amplitude_history > num_amplitudes:
        amplitude_sum -= amplitudes[ 0 ]
        amplitudes.pop( 0 )
        samples_in_amplitude_history -= sample_count

    amplitude_overall_average = amplitude_sum / samples_in_amplitude_history

    # Shift samples in time back to original phase and amplitude (using carrier)
    shifted_samples = [ y.real for y in [ (DC/AMPLITUDE) * (x / amplitude_overall_average - 1) for x in demodulated_samples ] ]

    # Low-pass filter
    filtered_samples, filter_state = scipy.signal.lfilter( filter_numer, filter_denom, shifted_samples, zi=filter_state )

    for i in range(len(filtered_samples)):
        if filtered_samples[i] < -5:
            filtered_samples[i] = -5
        if filtered_samples[i] > 5:
            filtered_samples[i] = 5
        if math.isnan( filtered_samples[i] ):
            filtered_samples[i] = 0
    
    return filtered_samples
    
