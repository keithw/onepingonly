import pyaudio
import sys
import struct
from math import *
import StringIO

# Link configuration
FORMAT = pyaudio.paFloat32
CHANNELS = 1
SAMPLES_PER_SECOND = 48000
CARRIER_CYCLES_PER_SECOND = 2000
CARRIER_CYCLES_PER_PREAMBLE_SYMBOL = 16
SECONDS_PER_CHUNK = 0.05
AMPLITUDE = 0.5
DC = 0.25
