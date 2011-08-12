from defs import *

# Derived quantities
SAMPLES_PER_CHUNK = int( SAMPLES_PER_SECOND * SECONDS_PER_CHUNK )

#print "Samples per chunk: %d" % SAMPLES_PER_CHUNK

# Open audio channel (input and output)
p = pyaudio.PyAudio()
stream = p.open(format = FORMAT,
                channels = CHANNELS,
                rate = SAMPLES_PER_SECOND,
                input = True,
                output = True,
                frames_per_buffer = SAMPLES_PER_CHUNK)

# Send one chunk of I samples, modulated onto the carrier frequency
def send( samples ):
    assert( len(samples) <= SAMPLES_PER_CHUNK )

    sample_count = 0
    chunk_data = ""
    TIME = 0 # seconds

    # Fill out samples to length of chunk
    while len(samples) < SAMPLES_PER_CHUNK:
        samples.append( 0 )

    # Write payload
    for x in samples:
        chunk_data += struct.pack( 'f', ((x * AMPLITUDE) + DC) * cos( CARRIER_CYCLES_PER_SECOND * TIME * 2 * pi ) )
        TIME += 1.0 / SAMPLES_PER_SECOND
        sample_count += 1

    # Send modulated samples
    stream.write( chunk_data )

def receive():
    samples = struct.unpack( 'f' * SAMPLES_PER_CHUNK,
                             stream.read( SAMPLES_PER_CHUNK ) )
    
    # Demodulate carrier
    demodulated_samples = []
    TIME = 0 # seconds
    average_amplitude = complex( 0, 0 )

    # Shift the modulated waveform back down to baseband
    for s in samples:
        I = s * cos( CARRIER_CYCLES_PER_SECOND * TIME * 2 * pi )
        Q = s * sin( CARRIER_CYCLES_PER_SECOND * TIME * 2 * pi )
        average_amplitude += complex( I, Q )
        demodulated_samples.append( complex( I, Q ) )
        TIME += 1.0 / SAMPLES_PER_SECOND

    # calculate average amplitude (DC amplitude)
    # we will use this for auto-gain control
    average_amplitude /= len(samples)

    # Shift samples in time back to original phase and amplitude (using carrier)
    if abs(average_amplitude) > 0.0001:
        shifted_samples = [ .5 * (x / average_amplitude - 1) for x in demodulated_samples ]
    else:
        shifted_samples = [ .5 * (x - 1) for x in demodulated_samples ]

    # Low-pass filter
    window = SAMPLES_PER_SECOND // CARRIER_CYCLES_PER_SECOND # floor division
    last_samples = [0] * window
    filtered_samples = []
    for i in shifted_samples:
        last_samples.pop( 0 )
        last_samples.append( i )
        filtered_samples.append( sum( last_samples ) / window )

    return filtered_samples
    
