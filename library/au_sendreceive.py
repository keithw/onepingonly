from au_send import *
from au_receive import *
import pyaudio

from au_defs import *

SAMPLES_PER_CHUNK = 32
DECIMATION_FACTOR = 1

class channel:
    def __call__( self, samples ):
        # prepare empty carrier
        samples_carrier = modulate( [0] * SAMPLES_PER_SECOND, SAMPLES_PER_CHUNK )

        # prepare modulated output
        samples_out = modulate( expand( samples, DECIMATION_FACTOR ), SAMPLES_PER_CHUNK )

        # send empty carrier
        for chunk in samples_carrier:
            raw_send( [chunk], self.soundcard_inout )
            raw_receive( SAMPLES_PER_CHUNK, self.soundcard_inout, SAMPLES_PER_CHUNK )

        # send output and collect input
        samples_in = []
        for chunk in samples_out:
            raw_send( [chunk], self.soundcard_inout )
            samples_in.extend( raw_receive( SAMPLES_PER_CHUNK, self.soundcard_inout, SAMPLES_PER_CHUNK ) )

        return decimate( demodulate( samples_in ), DECIMATION_FACTOR )

    def __init__( self ):
        self.id = "Audio"

        self.p = pyaudio.PyAudio()
        self.soundcard_inout = self.p.open(format = FORMAT,
                                           channels = CHANNELS,
                                           rate = SAMPLES_PER_SECOND,
                                           input = True,
                                           output = True,
                                           frames_per_buffer = SAMPLES_PER_CHUNK)

