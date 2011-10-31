from au_send import *
import au_receive
import pyaudio
import numpy

from au_defs import *

SAMPLES_PER_CHUNK = 128

class channel:
    def __call__( self, samples ):
        # open soundcard
        self.soundcard_inout = self.p.open(format = FORMAT,
                                           channels = CHANNELS,
                                           rate = SAMPLES_PER_SECOND,
                                           input = True,
                                           output = True,
                                           frames_per_buffer = SAMPLES_PER_CHUNK)

        # prepare premable
        packet = [-1] * 16384 + [0] * 16384
        for i in range( PREAMBLE_BITS / 2 ):
            packet.extend( self.zero )
            packet.extend( self.one )
        packet.extend( [0] * SECOND_CARRIER_LEN )

        packet.extend( samples )

        packet.extend( [0] * 256 )
        packet.extend( [-1] * 32768 )

        # prepare modulated output
        samples_out = modulate( packet, SAMPLES_PER_CHUNK )

        samples_in = []

        # send output and collect input
        for chunk in samples_out:
            raw_send( [chunk], self.soundcard_inout )
            samples_in.append( au_receive.raw_receive( SAMPLES_PER_CHUNK,
                                                       self.soundcard_inout, SAMPLES_PER_CHUNK ) )

        # demodulate input
        samples_all = numpy.concatenate( samples_in )
        ( preamble_end, offset_within_payload ) = self.detect_preamble( samples_all )

        # don't use payload as part of reference carrier
        # this allows us to correctly decode payload that doesn't sum to zero
        version2 = self.receiver.demodulate( samples_all[ preamble_end : ],
                                             include_this_carrier=False )

        if len(version2) - offset_within_payload < len(samples):
            print "warning: short packet( got %d, needed %d ). May need to lengthen trailer!" % ( len(version2) - offset_within_payload, len(samples) )
            return []
        assert( len(version2) - offset_within_payload >= len(samples) )

        self.soundcard_inout.close()

        return version2[offset_within_payload:offset_within_payload+len(samples)]

    def __init__( self ):
        self.id = "Audio"

        self.p = pyaudio.PyAudio()

        self.receiver = au_receive.Receiver()

        self.one = [1] * PREAMBLE_BIT_LEN
        self.zero = [-1] * PREAMBLE_BIT_LEN

    def detect_preamble( self, received_signal ):
        raw_received = numpy.concatenate( [self.receiver.demodulate(x) for x in numpy.array_split( received_signal, 256 )] )

        # find silent part of preamble
        silent_count = 0
        sample_id = 0
        while sample_id < len(raw_received):
            if abs( raw_received[ sample_id ] ) < 0.7:
                silent_count += 1
            else:
                silent_count = 0

            if silent_count >= 512:
                break # start looking for preamble bits
            sample_id += 1

        if silent_count < 512:
            print "Could not find silence before preamble -- too much noise?"
            return []

        print 'found carrier'

        preamble_start = -1
        preamble_last = -1

        # search for preamble bits
        preamble_bitsearch = -1
        preamble_bitcount = 0
        thisbit_count = 0
        while sample_id < len(raw_received):
            if raw_received[ sample_id ] * preamble_bitsearch >= 0.2:
                thisbit_count += 1
            else:
                thisbit_count = 0

            if thisbit_count >= PREAMBLE_BIT_LEN / 4:
                preamble_bitcount += 1
                preamble_bitsearch *= -1
                thisbit_count = 0
                if preamble_start < 0:
                    preamble_start = sample_id - PREAMBLE_BIT_LEN/4
                if preamble_last >= 0:
                    if sample_id - preamble_last >= 3 * PREAMBLE_BIT_LEN / 2:
                        print "WARNING: gap in preamble (of length %d) between bits %d and %d" % (sample_id - preamble_last, preamble_bitcount, preamble_bitcount - 1)
                        print "Restarting preamble detection"
                        preamble_start = sample_id - PREAMBLE_BIT_LEN/4
                        preamble_bitcount = 1
                        preamble_last = -1
                preamble_last = sample_id
            if preamble_bitcount == PREAMBLE_BITS:
                break
            sample_id += 1

        if preamble_bitcount != PREAMBLE_BITS:
            print "Could not find %d preamble bits, found only %d" % (PREAMBLE_BITS, preamble_bitcount)
            return []

        print 'found preamble'

        preamble_end = sample_id + 3*PREAMBLE_BIT_LEN/4

        # search for silence
        silent_count = 0
        while sample_id < len(raw_received):
            if abs( raw_received[ sample_id ] ) < 0.7:
                silent_count += 1
            else:
                silent_count = 0

            if silent_count >= SECOND_CARRIER_LEN/2:
                break
            sample_id += 1

        if silent_count != SECOND_CARRIER_LEN/2:
            print "Could not find silence after preamble"
            return []

        preamble_len = preamble_end - preamble_start

        print 'found second carrier'
        # now that we've identified the payload, use one AGC setting for whole thing
        self.receiver.clear_amplitude_history()

        # use preamble as the reference carrier for future demodulation
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

        return ( preamble_end, offset_within_payload )
