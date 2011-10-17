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

cachelen = 2048
COS_CACHE = [0] * cachelen
SIN_CACHE = [0] * cachelen
for i in range( cachelen ):
    COS_CACHE[ i ] = math.cos( CARRIER_CYCLES_PER_SECOND * TIME * 2 * math.pi )
    SIN_CACHE[ i ] = math.sin( CARRIER_CYCLES_PER_SECOND * TIME * 2 * math.pi )
    TIME += 1.0 / SAMPLES_PER_SECOND

COS_CACHE = numpy.array(COS_CACHE)
SIN_CACHE = numpy.array(SIN_CACHE)

num_amplitudes = 4096

PHASOR_CACHE = COS_CACHE + complex(0,1) * SIN_CACHE

nyquist_freq = float(SAMPLES_PER_SECOND) / 2.0

passband = float(CARRIER_CYCLES_PER_SECOND) / nyquist_freq

tuner_numer, tuner_denom = scipy.signal.iirdesign( [ passband * 0.75 * 1.025, passband * 1.25 * 0.975 ],
                                                   [ passband * 0.75 * 0.975, passband * 1.25 * 1.025 ],
                                                   1, 40 )

filter_numer, filter_denom = scipy.signal.iirdesign( passband * 0.85, passband * 0.95, 1, 30 )

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
    return (samples[::2], samples[1::2])

class TwoChannelReceiver:
    def __init__( self ):
        self.leftrec = Receiver()
        self.rightrec = Receiver()

    def receive( self, num_samples, stream, samples_per_chunk ):
        factor = int( 1.0 / passband )
        factor = 1

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
        self.amplitudes = [ 0 ]
        self.amplitude_sum = 0
        self.samples_in_amplitude_history = 0

        self.tuner_state = scipy.signal.lfiltic( tuner_numer, tuner_denom, [] )
        self.filter_state = scipy.signal.lfiltic( filter_numer, filter_denom, [] )

    def clear_amplitude_history( self ):
        self.amplitudes = []
        self.amplitude_sum = 0
        self.samples_in_amplitude_history = 0

    def amplification( self ):
        return 1/ abs(self.amplitude_sum / self.samples_in_amplitude_history)

    def demodulate( self, samples ):
        # Tune in band around carrier frequency
        samples, self.tuner_state = scipy.signal.lfilter( tuner_numer, tuner_denom, samples, zi=self.tuner_state )

        sample_count = len( samples )

        # Shift the modulated waveform back down to baseband
        demodulated_samples = samples * numpy.roll( PHASOR_CACHE, self.total_sample_count )[0:sample_count]
        self.total_sample_count += sample_count

        # calculate average amplitude (DC amplitude)
        # we will use this for auto gain control
        initializing = False
        if self.samples_in_amplitude_history == 0: # initializing
            initializing = True
            self.samples_in_amplitude_history = sample_count # we assume same value each call

        total_amplitude = sum( demodulated_samples )
        self.amplitudes.append( total_amplitude )
        self.amplitude_sum += total_amplitude
        self.samples_in_amplitude_history += sample_count

        while self.samples_in_amplitude_history > num_amplitudes:
            self.amplitude_sum -= self.amplitudes[ 0 ]
            self.amplitudes.pop( 0 )
            self.samples_in_amplitude_history -= sample_count

        if initializing:
            amplitude_overall_average = total_amplitude / sample_count
        else:
            amplitude_overall_average = self.amplitude_sum / self.samples_in_amplitude_history

        if amplitude_overall_average == 0:
            amplitude_overall_average = 1

        # Shift samples in time back to original phase and amplitude (using carrier)
        constant = 2*(DC/AMPLITUDE)/amplitude_overall_average
        constant2 = 2*DC/AMPLITUDE
        shifted_samples = demodulated_samples * constant - constant2

        shifted_samples = [x.real for x in shifted_samples]

        # Low-pass filter
        filtered_samples, self.filter_state = scipy.signal.lfilter( filter_numer, filter_denom, shifted_samples, zi=self.filter_state )
        
        return filtered_samples
    
