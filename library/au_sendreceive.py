from au_send import *
from au_receive import *
import pyaudio

from au_defs import *

SAMPLES_PER_CHUNK = 512

nyquist_freq = float(SAMPLES_PER_SECOND) / 2.0
passband = float(CARRIER_CYCLES_PER_SECOND) / nyquist_freq

DECIMATION_FACTOR = int( 1.0 / passband )

class channel:
    def __call__( self, samples ):
        # prepare premable
        packet = [0] * 8192
        one = [1] * 128
        zero = [-1] * 128
        for i in range( 8 ):
            packet.extend( one )
            packet.extend( zero )
        packet.extend( [0] * 128 )

        packet.extend( samples )

        packet.extend( [0] * 4096 )

        # prepare modulated output
        samples_out = modulate( expand( packet, DECIMATION_FACTOR), SAMPLES_PER_CHUNK )

        samples_in = []

        # send output and collect input
        for chunk in samples_out:
            raw_send( [chunk], self.soundcard_inout )
            samples_in.append( raw_receive( SAMPLES_PER_CHUNK,
                                            self.soundcard_inout, SAMPLES_PER_CHUNK ) )

        # demodulate input
        raw_received = []
        samples_all = []
        for chunk in samples_in:
            raw_received.extend( demodulate( chunk ) )
            samples_all.extend( chunk )

        raw_received = decimate( raw_received, DECIMATION_FACTOR )

        # find silent part of preamble
        silent_count = 0
        sample_id = 0
        while sample_id < len(raw_received):
            if abs( raw_received[ sample_id ] ) < 0.5:
                silent_count += 1
            else:
                silent_count = 0

            if silent_count >= 512:
                break # start looking for preamble bits
            sample_id += 1

        if silent_count < 512:
            print "Could not find silence before preamble"
            return []

        print 'found carrier'
        # search for preamble bits
        preamble_bitsearch = 1
        preamble_bitcount = 0
        thisbit_count = 0
        while sample_id < len(raw_received):
#            if raw_received[ sample_id ] * preamble_bitsearch >= 0.3:
            if raw_received[ sample_id ] * preamble_bitsearch >= 0.02:
                thisbit_count += 1
            else:
                thisbit_count = 0

            if thisbit_count >= 16:
                preamble_bitcount += 1
                preamble_bitsearch *= -1
                thisbit_count = 0
            if preamble_bitcount == 16:
                break
            sample_id += 1

        if preamble_bitcount != 16:
            print "Could not find 16 preamble bits, found only %d" % preamble_bitcount
            return []

        print 'found preamble'
        # search for silence
        silent_count = 0
        while sample_id < len(raw_received):
            if abs( raw_received[ sample_id ] ) < 0.5:
                silent_count += 1
            else:
                silent_count = 0

            if silent_count >= 128:
                break
            sample_id += 1

        if silent_count != 128:
            print "Could not find silence after preamble"
            return []

        print 'found second carrier'
        # now that we've identified the payload, use one AGC setting for whole thing
        clear_amplitude_history()
        version2 = decimate( demodulate( samples_all[ sample_id * DECIMATION_FACTOR : ] ),
                             DECIMATION_FACTOR )

        return version2[:len(samples)]

    def __init__( self ):
        self.id = "Audio"

        self.p = pyaudio.PyAudio()

        # open soundcard
        self.soundcard_inout = self.p.open(format = FORMAT,
                                           channels = CHANNELS,
                                           rate = SAMPLES_PER_SECOND,
                                           input = True,
                                           output = True,
                                           frames_per_buffer = SAMPLES_PER_CHUNK)
