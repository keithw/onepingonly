from au_send import *
import au_receive
import pyaudio
import numpy

from au_defs import *

SAMPLES_PER_CHUNK = 128

class Searcher:
    def __init__( self, samples ):
        self.i = 0
        self.samples = samples

    def find( self, threshold, description, match_length, greater_than=False, absolute_value=True ):
        matching_count = 0

        def matcher( x ):
            def val4val( x ):
                if absolute_value: return abs(x)
                else: return x

            def test( x, y ):
                if greater_than: return x > y
                else: return x < y

            return test( val4val( x ), val4val( threshold ) )

        while self.i < len(self.samples):
            if matcher( self.samples[ self.i ] ):
                matching_count += 1
            else:
                matching_count = 0

            if matching_count >= match_length:
                break

            self.i += 1

        if matching_count < match_length:
            raise Exception( "Could not find %s" % description )
        
        return self.i - match_length

class channel:
    def prepend_preamble( self, samples ):
        # prepare premable
        signal = [-1] * 16384 + [0] * 16384
        for i in range( PREAMBLE_BITS / 2 ):
            signal.extend( self.zero )
            signal.extend( self.one )
        signal.extend( [0] * SECOND_CARRIER_LEN )

        signal.extend( samples )

        signal.extend( [0] * 256 )
        signal.extend( [-1] * 32768 )

        # prepare modulated output
        samples_out = modulate( signal, SAMPLES_PER_CHUNK )

        return samples_out

    def extract_payload( self, signal, payload_len ):
        # find preamble in received signal
        ( preamble_start, payload_start ) = self.detect_preamble( signal )

        # demodulate payload using carrier reference from preamble
        version2 = self.receiver.demodulate( signal[ preamble_start: ],
                                             carrier=self.receiver.reference_carrier )

        extracted_payload = version2[payload_start-preamble_start:payload_start-preamble_start+payload_len]
        assert( len(extracted_payload) == payload_len )

        return extracted_payload

    def __call__( self, samples ):
        # open soundcard
        self.soundcard_inout = self.p.open(format = FORMAT,
                                           channels = CHANNELS,
                                           rate = SAMPLES_PER_SECOND,
                                           input = True,
                                           output = True,
                                           frames_per_buffer = SAMPLES_PER_CHUNK)

        samples_out = self.prepend_preamble( samples )
        samples_in = []

        # send output and collect input
        for chunk in samples_out:
            raw_send( [chunk], self.soundcard_inout )
            samples_in.append( au_receive.raw_receive( SAMPLES_PER_CHUNK,
                                                       self.soundcard_inout, SAMPLES_PER_CHUNK ) )

        self.soundcard_inout.close()

        # demodulate input
        samples_all = numpy.concatenate( samples_in )

        return self.extract_payload( samples_all, len( samples ) )

    def __init__( self ):
        self.id = "Audio"

        self.p = pyaudio.PyAudio()

        self.receiver = au_receive.Receiver( 2500, 500 )

        self.one = [1] * PREAMBLE_BIT_LEN
        self.zero = [-1] * PREAMBLE_BIT_LEN

    def detect_preamble( self, received_signal ):
        demodulation_chunk = PREAMBLE_BIT_LEN * 4

        if len( received_signal ) % demodulation_chunk != 0:
            received.signal = numpy.concatenate( received_signal, numpy.zeros( len(received_signal) % demodulation_chunk ) )

        # first, rough demodulation
        raw_received = numpy.concatenate( [self.receiver.demodulate(x) for x in numpy.split( received_signal, len(received_signal) / demodulation_chunk )] )

        searcher = Searcher( raw_received )

        # find silent part of preamble
        searcher.find( 0.7, "first tone in preamble", 512 )

        print "Found first tone in preamble"

        # search for preamble bits
        preamble_last = -1
        preamble_start = -1
        preamble_bits_found = 0
        while preamble_bits_found < PREAMBLE_BITS:
            bit_polarity = (preamble_bits_found % 2) * 2 - 1
            preamble_thisbit = searcher.find( 0.2 * bit_polarity,
                                              ("preamble bit %d" % preamble_bits_found), PREAMBLE_BIT_LEN / 4,
                                              greater_than=(bit_polarity==1),
                                              absolute_value=False )

            preamble_bits_found += 1

            if preamble_start < 0:
                preamble_start = preamble_thisbit

            if preamble_last >= 0:
                if preamble_thisbit - preamble_last >= 2 * PREAMBLE_BIT_LEN:
                    print "WARNING: gap in preamble (of length %d) between bits %d and %d" % (preamble_thisbit - preamble_last, preamble_bits_found, preamble_bits_found - 1)
                    print "Restarting preamble detection"
                    preamble_bits_found = 1
                    preamble_start = preamble_thisbit
                    preamble_last = -1

            preamble_last = preamble_thisbit

        print 'Found preamble'

        preamble_end = preamble_thisbit + 3*PREAMBLE_BIT_LEN/4

        # search for silence
        searcher.find( 0.7, "second tone in preamble", SECOND_CARRIER_LEN/2 )

        print "Found second tone in preamble"

        preamble_len = preamble_end - preamble_start

        # now that we've identified the payload, use one AGC setting for whole thing

        # second, better demodulation
        preamble_decoded = self.receiver.demodulate( received_signal[ preamble_start : preamble_end ] )

        # find REAL phase of preamble
        expected_preamble = []
        for i in range( PREAMBLE_BITS / 2 ):
            expected_preamble.extend( self.zero )
            expected_preamble.extend( self.one )

        out_of_phase_preamble = self.one[:PREAMBLE_BIT_LEN/2]
        out_of_phase_preamble.extend( expected_preamble )
        out_of_phase_preamble = out_of_phase_preamble[0:len(expected_preamble)]

        if abs(len(preamble_decoded) - len(expected_preamble)) > PREAMBLE_BIT_LEN/2:
            print "Warning: Preamble offset too great to be corrected -- too much noise?"
            print "preamble_start: %d, preamble_end: %d, expected_preamble: %d" % (preamble_start, preamble_end, len(expected_preamble))
            return []
        
        # equalize lengths
        expected_preamble = expected_preamble[0:len(preamble_decoded)]
        out_of_phase_preamble = out_of_phase_preamble[0:len(preamble_decoded)]
        preamble_decoded_trunc = preamble_decoded[0:len(expected_preamble)]

        # find phase and offset (in samples) of preamble
        preamble_I = numpy.dot(preamble_decoded_trunc, numpy.array(expected_preamble))
        preamble_Q = numpy.dot(preamble_decoded_trunc, numpy.array(out_of_phase_preamble))

        offset = int(0.5 + PREAMBLE_BIT_LEN * math.atan2( preamble_Q, preamble_I ) / math.pi)

        print "Preamble was offset %d samples relative to initial rough detection" % (offset)

        payload_start = preamble_start + offset + PREAMBLE_BIT_LEN * PREAMBLE_BITS + SECOND_CARRIER_LEN

        assert( payload_start > preamble_end )

        offset_within_payload = payload_start - preamble_end

        return ( preamble_start, payload_start )
