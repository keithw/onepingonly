from au_send import *
import au_receive
import pyaudio
import numpy

from au_defs import *

SAMPLES_PER_CHUNK = 512

nyquist_freq = float(SAMPLES_PER_SECOND) / 2.0
passband = float(CARRIER_CYCLES_PER_SECOND) / nyquist_freq

DECIMATION_FACTOR = int( 1.0 / passband )

PREAMBLE_BITS = 32
PREAMBLE_BIT_LEN = 128
SECOND_CARRIER_LEN = 512

class channel:
    def __call__( self, samples ):
        # prepare premable
        packet = [0] * 8192
        one = [1] * PREAMBLE_BIT_LEN
        zero = [-1] * PREAMBLE_BIT_LEN
        for i in range( PREAMBLE_BITS / 2 ):
            packet.extend( one )
            packet.extend( zero )
        packet.extend( [0] * SECOND_CARRIER_LEN )

        packet.extend( samples )

        packet.extend( [0] * 128 )
        packet.extend( [-1] * 16384 )

        # prepare modulated output
        samples_out = modulate( expand( packet, DECIMATION_FACTOR), SAMPLES_PER_CHUNK )

        samples_in = []

        # send output and collect input
        for chunk in samples_out:
            raw_send( [chunk], self.soundcard_inout )
            samples_in.append( au_receive.raw_receive( SAMPLES_PER_CHUNK,
                                                       self.soundcard_inout, SAMPLES_PER_CHUNK ) )

        # demodulate input
        raw_received = []
        samples_all = []
        for chunk in samples_in:
            raw_received.extend( self.receiver.demodulate( chunk ) )
            samples_all.extend( chunk )

        raw_received = au_receive.decimate( raw_received, DECIMATION_FACTOR )

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

        preamble_start = -1

        # search for preamble bits
        preamble_bitsearch = 1
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
                    preamble_start = sample_id - PREAMBLE_BIT_LEN / 2 # include some carrier
            if preamble_bitcount == PREAMBLE_BITS:
                break
            sample_id += 1

        if preamble_bitcount != PREAMBLE_BITS:
            print "Could not find %d preamble bits, found only %d" % (PREAMBLE_BITS, preamble_bitcount)
            return []

        print 'found preamble'
        # search for silence
        silent_count = 0
        while sample_id < len(raw_received):
            if abs( raw_received[ sample_id ] ) < 0.5:
                silent_count += 1
            else:
                silent_count = 0

            if silent_count >= SECOND_CARRIER_LEN/2:
                break
            sample_id += 1

        if silent_count != SECOND_CARRIER_LEN/2:
            print "Could not find silence after preamble"
            return []

        preamble_end = sample_id

        preamble_len = preamble_end - preamble_start

        print 'found second carrier'
        # now that we've identified the payload, use one AGC setting for whole thing
        self.receiver.clear_amplitude_history()

        # use preamble as the reference carrier for future demodulation
        preamble_decoded = au_receive.decimate( self.receiver.demodulate( samples_all[ preamble_start * DECIMATION_FACTOR : preamble_end * DECIMATION_FACTOR ] ),
                                                DECIMATION_FACTOR )

        # find REAL phase of preamble
        expected_preamble = []
        for i in range( PREAMBLE_BITS / 2 ):
            expected_preamble.extend( one )
            expected_preamble.extend( zero )

        out_of_phase_preamble = zero[:PREAMBLE_BIT_LEN/2]
        out_of_phase_preamble.extend( expected_preamble )
        out_of_phase_preamble = out_of_phase_preamble[0:len(expected_preamble)]

        assert( abs(len(preamble_decoded) - PREAMBLE_BIT_LEN/4 - SECOND_CARRIER_LEN/2 - len(expected_preamble)) <= PREAMBLE_BIT_LEN/2 )
        
        # equalize lengths
        expected_preamble = expected_preamble[0:len(preamble_decoded)]
        out_of_phase_preamble = out_of_phase_preamble[0:len(preamble_decoded)]
        preamble_decoded_trunc = preamble_decoded[0:len(expected_preamble)]

        # find phase and offset (in samples) of preamble
        preamble_I = numpy.dot(preamble_decoded_trunc, numpy.array(expected_preamble))
        preamble_Q = numpy.dot(preamble_decoded_trunc, numpy.array(out_of_phase_preamble))

        offset = int(0.5 + PREAMBLE_BIT_LEN * math.atan2( preamble_Q, preamble_I ) / math.pi)

        print "Preamble was offset %d samples relative to initial rough detection" % (offset - (PREAMBLE_BIT_LEN/4))

        # find signal-to-noise ratio (just for fun)
        max_power = 0
        signal_power = 0
        noise_power = 0
        noise_average = 0
        one = numpy.array(one)
        zero = numpy.array(zero)
        for i in range( PREAMBLE_BITS / 2 ):
            this_offset = offset + i * PREAMBLE_BIT_LEN*2
            preamble_one = preamble_decoded[ this_offset : this_offset + PREAMBLE_BIT_LEN ]
            preamble_zero = preamble_decoded[ this_offset + PREAMBLE_BIT_LEN : this_offset + 2 * PREAMBLE_BIT_LEN ]
            
            signal_power += sum(preamble_one * preamble_one) + sum(preamble_zero * preamble_zero)
            max_power += sum(one * one) + sum(zero * zero)
            average_one = sum(preamble_one) / len(preamble_one)
            average_zero = sum(preamble_zero) / len(preamble_zero)
            one_diff = preamble_one - numpy.array([average_one] * PREAMBLE_BIT_LEN)
            zero_diff = preamble_zero - numpy.array([average_zero] * PREAMBLE_BIT_LEN)
            noise_power += sum(one_diff * one_diff) + sum(zero_diff * zero_diff)

        if signal_power / max_power < 0.3:
            print "WARNING: Preamble power very low relative to expected"
            print "We probably did not correctly detect this packet."
            return []

        snr = signal_power / noise_power
        snr_in_db = 10 * math.log10(snr)
        print "Signal-to-noise ratio: %.2f dB" % snr_in_db

        payload_start = preamble_start + offset + PREAMBLE_BIT_LEN * PREAMBLE_BITS + SECOND_CARRIER_LEN

        assert( payload_start > preamble_end )

        # don't use payload as part of reference carrier
        # this allows us to correctly decode payload that doesn't sum to zero
        version2 = au_receive.decimate( self.receiver.demodulate( samples_all[ preamble_end * DECIMATION_FACTOR : ],
                                                                  include_this_carrier=False ),
                                        DECIMATION_FACTOR )

        offset_within_payload = payload_start - preamble_end

        if len(version2) - offset_within_payload < len(samples):
            print "warning: short packet. May need to lengthen trailer!"
        assert( len(version2) - offset_within_payload >= len(samples) )

        return version2[offset_within_payload:offset_within_payload+len(samples)]

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

        self.receiver = au_receive.Receiver()
