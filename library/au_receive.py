import pyaudio
import sys
import struct
import math
import StringIO
import numpy
import scipy.signal

from au_filter import Filter

from au_defs import *

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
        leftsamp, rightsamp = raw_receive( num_samples, stream, samples_per_chunk )
        leftsamp = self.leftrec.demodulate( leftsamp )
        rightsamp = self.rightrec.demodulate( rightsamp )
        return (leftsamp, rightsamp)

    def amplification( self ):
        return ( self.leftrec.amplification(), self.rightrec.amplification() )

class Receiver:
    def receive( self, num_samples, stream, samples_per_chunk ):
        return self.demodulate( raw_receive( num_samples, stream, samples_per_chunk ) )

    def __init__( self, center_frequency, bandwidth ):
        self.reference_carrier = 1

        self.tuner = Filter( center_frequency - bandwidth, center_frequency + bandwidth )
        self.lowpass = Filter( 0, bandwidth )

    def demodulate( self, samples, carrier=0 ):
        sample_count = len( samples )

        # Tune in band around carrier frequency
        samples = self.tuner( samples )

        # Shift the modulated waveform back down to baseband
        SAMPLES = numpy.arange( 0, sample_count )
        ARGS = SAMPLES * (CARRIER_CYCLES_PER_SECOND * 2.0 * math.pi / SAMPLES_PER_SECOND)
        LOCAL_CARRIER = numpy.cos(ARGS) + complex(0,1) * numpy.sin(ARGS)
        demodulated_samples = samples * LOCAL_CARRIER

        # calculate average amplitude (DC amplitude)
        # we will use this for auto gain control
        if carrier==0:
            carrier = sum( demodulated_samples ) / sample_count

        self.reference_carrier = carrier

        # Shift samples in time back to original phase and amplitude (using carrier)
        constant = (DC/AMPLITUDE)/carrier
        constant2 = DC/AMPLITUDE
        shifted_samples = demodulated_samples * constant - constant2

        shifted_samples = [x.real for x in shifted_samples]

        # Low-pass filter
        filtered_samples = self.lowpass( shifted_samples )
        
        return filtered_samples
    
