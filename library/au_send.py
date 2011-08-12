from au_defs import *

# Open audio channel (input and output)
p = pyaudio.PyAudio()
stream = p.open(format = FORMAT,
                channels = CHANNELS,
                rate = SAMPLES_PER_SECOND,
                input = False,
                output = True,
                frames_per_buffer = SAMPLES_PER_SECOND * SECONDS_PER_CHUNK)

# Send one chunk of I samples, modulated onto the carrier frequency
def send( samples ):
    SAMPLES_PER_CHUNK = SAMPLES_PER_SECOND * SECONDS_PER_CHUNK
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
