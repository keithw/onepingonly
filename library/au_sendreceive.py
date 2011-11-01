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
    def send_voltage_samples( self, samples ):
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
        samples_out = modulate_float( signal, self.carrier_freq, SAMPLES_PER_CHUNK )

        return samples_out

    def extract_payload( self, signal, payload_len ):
        # find preamble in received signal
        ( preamble_start, payload_start ) = self.detect_preamble( signal )

        # demodulate payload
        slice_start = payload_start - 3*SECOND_CARRIER_LEN/4
        slice_end = payload_start + payload_len
        extracted_payload = self.receiver.demodulate( signal[ slice_start : slice_end ] )[ payload_start - slice_start: ]

        if len( extracted_payload ) != payload_len:
            raise Exception( "WARNING: Only received %d of %d samples sent" % ( len(extracted_payload),
                                                                                payload_len ) )

        return extracted_payload

    def __call__( self, samples ):
        # open soundcard
        self.soundcard_inout = self.p.open(format = FORMAT,
                                           channels = CHANNELS,
                                           rate = SAMPLES_PER_SECOND,
                                           input = True,
                                           output = True,
                                           frames_per_buffer = SAMPLES_PER_CHUNK)

        samples_out = self.send_voltage_samples( samples )
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

    def __init__( self, carrier_freq, bandwidth ):
        self.id = "Audio"

        self.p = pyaudio.PyAudio()

        self.carrier_freq = carrier_freq
        self.bandwidth = bandwidth

        self.receiver = au_receive.Receiver( carrier_freq, bandwidth )

        self.one = [1] * PREAMBLE_BIT_LEN
        self.zero = [-1] * PREAMBLE_BIT_LEN

        self.f1 = Filter( self.carrier_freq - self.bandwidth, self.carrier_freq + self.bandwidth )
        self.f2 = Filter( 0, self.bandwidth )

    def detect_preamble( self, received_signal ):
        demodulation_chunk = PREAMBLE_BIT_LEN * 4

        # make sure length is even multiple of demodulation chunk size
        if len( received_signal ) % demodulation_chunk != 0:
            received_signal = numpy.hstack( (received_signal, 
                                             numpy.zeros( demodulation_chunk - (len(received_signal) % demodulation_chunk) ) ) )

        # first, rough demodulation
        raw_received = numpy.concatenate( [self.dmd(x) for x in numpy.split( received_signal, len(received_signal) / demodulation_chunk )] )

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

        # now that we've identified the preamble, demodulate it again using a single local carrier
        slice_start = preamble_start - 3*SECOND_CARRIER_LEN/4
        slice_end = preamble_end + 3*SECOND_CARRIER_LEN/4
        preamble_decoded = self.dmd( received_signal[ slice_start : slice_end ] )[ preamble_start - slice_start:
                                                                                                       preamble_end - slice_start ]

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

    def dmd( self, samples ):
        args = numpy.arange(0,len(samples)) * self.carrier_freq * 2 * math.pi / SAMPLES_PER_SECOND
        ds = self.f1( samples ) * (numpy.cos(args) + complex(0,1) * numpy.sin(args))
        return self.f2( [x.real for x in (len(samples)*ds/sum(ds) - 1) * DC/AMPLITUDE] )
