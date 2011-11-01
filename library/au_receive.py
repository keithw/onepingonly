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
        self.carrier_freq = center_frequency

        self.tuner = Filter( center_frequency - bandwidth, center_frequency + bandwidth )
        self.lowpass = Filter( 0, bandwidth )

    def demodulate( self, samples ):
        print "Running demodulate()"

        # Tune in just a band around the carrier frequency
        samples = self.tuner( samples )

        # Shift the modulated waveform back down to baseband
        # By multiplying by a complex exponential

        # First, we make the complex exponential (the local carrier)
        args = numpy.arange(0,len(samples)) * self.carrier_freq * 2 * math.pi / SAMPLES_PER_SECOND
        local_carrier = numpy.cos(args) + complex(0,1) * numpy.sin(args)

        # Now, we shift down to baseband (and also up to 2x LOCAL_CARRIER)
        demodulated_samples = samples * local_carrier

        # We assume the transmitted data had equal zeros and ones, and therefore
        # that the average value is the (complex) amplitude of the carrier
        estimated_carrier = sum( demodulated_samples ) / len( samples )

        # Rotate and shift samples in time back to original phase and amplitude,
        # including subtracting off the DC offset
        shifted_samples = (demodulated_samples/estimated_carrier - 1) * DC/AMPLITUDE

        # Throw out the imaginary part
        shifted_samples = [x.real for x in shifted_samples]

        # Low-pass filter to remove 2x carrier component
        filtered_samples = self.lowpass( shifted_samples )
        
        return filtered_samples
