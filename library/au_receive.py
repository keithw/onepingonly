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
                input = True,
                output = False,
                frames_per_buffer = SAMPLES_PER_CHUNK)

def receive():
    samples = struct.unpack( 'f' * SAMPLES_PER_CHUNK,
                             stream.read( SAMPLES_PER_CHUNK ) )

    # Demodulate carrier
    demodulated_samples = []
    TIME = 0 # seconds
    average_amplitude = complex( 0, 0 )

    # Shift the modulated waveform back down to baseband
    for s in samples:
        I = s * math.cos( CARRIER_CYCLES_PER_SECOND * TIME * 2 * math.pi )
        Q = s * math.sin( CARRIER_CYCLES_PER_SECOND * TIME * 2 * math.pi )
        average_amplitude += complex( I, Q )
        demodulated_samples.append( complex( I, Q ) )
        TIME += 1.0 / SAMPLES_PER_SECOND

    # calculate average amplitude (DC amplitude)
    # we will use this for auto-gain control
    average_amplitude /= len(samples)

    # Shift samples in time back to original phase and amplitude (using carrier)
    shifted_samples = [ .5 * (x / average_amplitude - 1) for x in demodulated_samples ]

    # Low-pass filter
    window = SAMPLES_PER_SECOND // CARRIER_CYCLES_PER_SECOND
    last_samples = [0] * window
    filtered_samples = []
    for i in shifted_samples:
        last_samples.pop( 0 )
        last_samples.append( i )
        filtered_samples.append( sum( last_samples ) / window )

    return filtered_samples
    
