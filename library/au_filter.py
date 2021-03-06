from scipy.signal import iirdesign, lfiltic, lfilter
from au_defs import *

class Filter:
    def __init__( self, band_start, band_stop ):
        nyquist_frequency = float(SAMPLES_PER_SECOND) / 2.0
        
        band_start /= nyquist_frequency
        band_stop /= nyquist_frequency

        assert( band_start >= 0 and band_start <= 1 )
        assert( band_stop >= 0 and band_stop <= 1 )
        assert( band_stop >= band_start )

        passband_edges = []
        stopband_edges = []

        if band_start >= 0.05: # if not, make LPF only
            passband_edges.append( band_start * 1.025 )
            stopband_edges.append( band_start * 0.975 )

        if band_stop <= 0.95: # if not, make HPF only
            passband_edges.append( band_stop * 0.975 )
            stopband_edges.append( band_stop * 1.025 )

        (self.feedforward_taps,
         self.feedback_taps) = iirdesign( passband_edges,
                                          stopband_edges,
                                          0.1,               # max attenuation (dB) in passband
                                          30 )               # min attenuation (dB) in stopband

        self.filter_state = lfiltic( self.feedforward_taps, self.feedback_taps, [] )

    def __call__( self, samples ):
        (filtered_samples,
         self.filter_state) = lfilter( self.feedforward_taps,
                                       self.feedback_taps,
                                       samples,
                                       zi=self.filter_state )
        return filtered_samples
