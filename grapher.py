#!/usr/bin/python

import pyaudio
import sys
import struct
import math
import pygtk
import gtk
import gobject
import cmath

WIDTH=512
HEIGHT=512

# set up plot
window = gtk.Window(gtk.WINDOW_TOPLEVEL)
drawing_area = gtk.DrawingArea()
drawing_area.set_size_request(WIDTH, HEIGHT)
window.add( drawing_area )
drawing_area.show()
window.show()
drawable = drawing_area.window
pixmap = gtk.gdk.Pixmap(drawable, WIDTH, HEIGHT, depth=-1)
context = pixmap.new_gc()
colormap = drawing_area.get_colormap()
fg = colormap.alloc_color( "blue" )
fg2 = colormap.alloc_color( "green" )
bg = colormap.alloc_color( "white" )
axes = colormap.alloc_color( "black" )

FORMAT = pyaudio.paFloat32
CHANNELS = 1
SAMPLE_RATE = 48000
FREQ = 1000
CYCLES_PER_BIT = 4
BIT = int(SAMPLE_RATE*CYCLES_PER_BIT/FREQ)
CHUNK = int(16 * BIT)
BIT_RATE = SAMPLE_RATE / BIT

p = pyaudio.PyAudio()

stream = p.open(format = FORMAT,
                channels = CHANNELS,
                rate = SAMPLE_RATE,
                input = True,
                output = False,
                frames_per_buffer = CHUNK)

TIME = 0 # seconds

cosines = []
sines = []

bitclockH_I = []
bitclockH_Q = []
bitclockL_I = []
bitclockL_Q = []

def square(x):
    if x > 0:
        return 1
    else:
        return -1

for i in range(CHUNK*2):
    cosines.append( math.cos( FREQ * TIME * (2 * math.pi) ) )
    sines.append( math.sin( FREQ * TIME * (2 * math.pi) ) )

    bitclockH_I.append( square( math.cos( (FREQ+BIT_RATE/2.0) * TIME * (2 * math.pi) ) ) )
    bitclockH_Q.append( square( math.sin( (FREQ+BIT_RATE/2.0) * TIME * (2 * math.pi) ) ) )
    bitclockL_I.append( square( math.cos( (FREQ-BIT_RATE/2.0) * TIME * (2 * math.pi) ) ) )
    bitclockL_Q.append( square( math.sin( (FREQ-BIT_RATE/2.0) * TIME * (2 * math.pi) ) ) )

    TIME += 1.0 / SAMPLE_RATE

def capture_audio(*args):
    # Listen for a tenth of a second
    received_signal = struct.unpack("f"*CHUNK, stream.read(CHUNK))

    # clear screen and draw axes
    context.foreground = bg
    pixmap.draw_rectangle(context, True, 0, 0, WIDTH, HEIGHT )
    context.foreground = axes
    pixmap.draw_line( context, int(WIDTH/2), 0, int(WIDTH/2), HEIGHT )
    pixmap.draw_line( context, 0, int(HEIGHT/2), WIDTH, int(HEIGHT/2) )

    # find bit offset
    a = 0.0
    b = 0.0
    c = 0.0
    d = 0.0
    for i in range(CHUNK):
        a += received_signal[ i ] * bitclockL_I[ i ] / CHUNK
        b += received_signal[ i ] * bitclockL_Q[ i ] / CHUNK
        c += received_signal[ i ] * bitclockH_I[ i ] / CHUNK
        d += received_signal[ i ] * bitclockH_Q[ i ] / CHUNK

    if abs(complex(c, d)) == 0:
        offset = 0
    else:
        offset = int( (math.pi + cmath.phase( complex(a, b) / complex( c, d ) )) * BIT / (2 * math.pi) )

    print "offset: %d" % offset

    # Find amplitude of each bit
    position_in_chunk = 0
    for bit in range(CHUNK/BIT):
        sine_amplitude = 0.0
        cosine_amplitude = 0.0
        for i in range(BIT):
            cosine_amplitude += received_signal[ position_in_chunk ] * cosines[ position_in_chunk ] / BIT
            sine_amplitude +=   received_signal[ position_in_chunk ] * sines[ position_in_chunk ] / BIT
            position_in_chunk += 1

        mag = math.sqrt( cosine_amplitude**2 + sine_amplitude**2 ) * 1000
        theta = math.degrees( math.atan2( sine_amplitude, cosine_amplitude ) )

        # draw bit
        context.foreground = fg
        x_coor = (WIDTH/2) + (cosine_amplitude*5) * (WIDTH/2)
        y_coor = (HEIGHT/2) + (sine_amplitude*5) * (HEIGHT/2)

        pixmap.draw_rectangle(context, True, int(x_coor)-5, int(y_coor)-5, 10, 10 )

    position_in_chunk = 0
    for bit in range((CHUNK-BIT)/BIT):
        sine_amplitude = 0.0
        cosine_amplitude = 0.0
        for i in range(BIT):
            cosine_amplitude += received_signal[ position_in_chunk+BIT-offset ] * cosines[ position_in_chunk ] / BIT
            sine_amplitude   += received_signal[ position_in_chunk+BIT-offset ] * sines[ position_in_chunk ] / BIT
            position_in_chunk += 1

        mag = math.sqrt( cosine_amplitude**2 + sine_amplitude**2 ) * 1000
        theta = math.degrees( math.atan2( sine_amplitude, cosine_amplitude ) )

        # draw bit
        context.foreground = fg2
        x_coor = (WIDTH/2) + (cosine_amplitude*5) * (WIDTH/2)
        y_coor = (HEIGHT/2) + (sine_amplitude*5) * (HEIGHT/2)

        pixmap.draw_rectangle(context, True, int(x_coor)-3, int(y_coor)-3, 6, 6 )

    # blit to screen
    drawable.draw_drawable( context, pixmap, 0, 0, 0, 0, -1, -1 )

#    print mag, theta
    return True

gobject.idle_add(capture_audio)
gtk.main()

stream.stop_stream()
stream.close()
p.terminate()
