import pyaudio
import sys
import struct
import math
import StringIO
import numpy
import scipy.signal

from au_filter import Filter

from au_defs import *

assert( abs( (float(SAMPLES_PER_SECOND) / float(CARRIER_CYCLES_PER_SECOND)) - (SAMPLES_PER_SECOND // CARRIER_CYCLES_PER_SECOND) ) < 0.01 )

num_amplitudes = 4096

nyquist_freq = float(SAMPLES_PER_SECOND) / 2.0
passband = float(CARRIER_CYCLES_PER_SECOND) / nyquist_freq

def decimate( samples, factor ):
    return samples[::factor]

def raw_receive( num_samples, stream, samples_per_chunk ):
    sample_count = 0
    samples = []
    while sample_count < num_samples:
        try:
            samples.extend( struct.unpack( 'f' * samples_per_chunk * CHANNELS,
                                           stream.read( samples_per_chunk ) ) )
            sample_count += samples_per_chunk
        except IOError:
            sys.stderr.write( "IOError\n" )
            pass

    assert( sample_count == num_samples )
    samples = numpy.array(samples)

    if CHANNELS == 2:
        return (samples[::2], samples[1::2])
    else:
        return samples

class TwoChannelReceiver:
    def __init__( self ):
        self.leftrec = Receiver()
        self.rightrec = Receiver()

    def receive( self, num_samples, stream, samples_per_chunk ):
        factor = int( 1.0 / passband )

        leftsamp, rightsamp = raw_receive( num_samples * factor, stream, samples_per_chunk )
        leftsamp = self.leftrec.demodulate( leftsamp )[::factor]
        rightsamp = self.rightrec.demodulate( rightsamp )[::factor]
        return (leftsamp, rightsamp)

    def amplification( self ):
        return ( self.leftrec.amplification(), self.rightrec.amplification() )

class Receiver:
    def receive( self, num_samples, stream, samples_per_chunk ):
        factor = int( 1.0 / passband )
        return self.demodulate( raw_receive( num_samples * factor, stream, samples_per_chunk ) )[::factor]

    def __init__( self ):
        self.total_sample_count = 0
        self.amplitudes = []
        self.amplitude_sum = 0
        self.samples_in_amplitude_history = 0

        self.tuner = Filter( 1000, 3000 )
        self.lowpass = Filter( 0, 2000 )

    def clear_amplitude_history( self ):
        self.amplitudes = []
        self.amplitude_sum = 0
        self.samples_in_amplitude_history = 0

    def amplification( self ):
        return 1/ abs(self.amplitude_sum / self.samples_in_amplitude_history)

    def demodulate( self, samples, include_this_carrier=True ):
        sample_count = len( samples )

        # Tune in band around carrier frequency
        samples = self.tuner( samples )

        # Shift the modulated waveform back down to baseband
        SAMPLES = numpy.arange( self.total_sample_count, self.total_sample_count + sample_count )
        ARGS = SAMPLES * (CARRIER_CYCLES_PER_SECOND * 2.0 * math.pi / SAMPLES_PER_SECOND)
        LOCAL_CARRIER = numpy.cos(ARGS) + complex(0,1) * numpy.sin(ARGS)
        demodulated_samples = samples * LOCAL_CARRIER
        self.total_sample_count += sample_count

        # calculate average amplitude (DC amplitude)
        # we will use this for auto gain control
        if include_this_carrier:
            total_amplitude = sum( demodulated_samples )
            self.amplitudes.append( (total_amplitude, sample_count) )
            self.amplitude_sum += total_amplitude 
            self.samples_in_amplitude_history += sample_count

            while self.samples_in_amplitude_history - self.amplitudes[ 0 ][ 1 ] >= num_amplitudes:
                self.amplitude_sum -= self.amplitudes[ 0 ][ 0 ]
                self.samples_in_amplitude_history -= self.amplitudes[ 0 ][ 1 ]
                self.amplitudes.pop( 0 )

        amplitude_overall_average = self.amplitude_sum / self.samples_in_amplitude_history

        if not include_this_carrier:
            self.clear_amplitude_history()

        if amplitude_overall_average == 0:
            amplitude_overall_average = 1

        # Shift samples in time back to original phase and amplitude (using carrier)
        constant = 2*(DC/AMPLITUDE)/amplitude_overall_average
        constant2 = 2*DC/AMPLITUDE
        shifted_samples = demodulated_samples * constant - constant2

        shifted_samples = [x.real for x in shifted_samples]

        # Low-pass filter
        filtered_samples = self.lowpass( shifted_samples )
        
        return filtered_samples
    
