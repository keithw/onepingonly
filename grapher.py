#!/usr/bin/python

import pyaudio
import sys
import struct
import math
import pygtk
import gtk
import gobject

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
bg = colormap.alloc_color( "white" )
axes = colormap.alloc_color( "black" )

FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 48000
FREQ = 1000
CYCLES_PER_BIT = 4
BIT = int(RATE*CYCLES_PER_BIT/FREQ)
CHUNK = int(16 * BIT)

p = pyaudio.PyAudio()

stream = p.open(format = FORMAT,
                channels = CHANNELS,
                rate = RATE,
                input = True,
                output = False,
                frames_per_buffer = CHUNK)

TIME = 0 # seconds

def capture_audio(*args):
    global TIME

    cosines = []
    sines = []
    for i in range(CHUNK):
        cosines.append( math.cos( FREQ * TIME * (2 * math.pi) ) )
        sines.append( math.sin( FREQ * TIME * (2 * math.pi) ) )
        TIME += 1.0 / RATE

    # Listen for a tenth of a second
    received_signal = struct.unpack("f"*CHUNK, stream.read(CHUNK))

    # clear screen and draw axes
    context.foreground = bg
    pixmap.draw_rectangle(context, True, 0, 0, WIDTH, HEIGHT )
    context.foreground = axes
    pixmap.draw_line( context, int(WIDTH/2), 0, int(WIDTH/2), HEIGHT )
    pixmap.draw_line( context, 0, int(HEIGHT/2), WIDTH, int(HEIGHT/2) )

    # Find amplitude of each bit
    position_in_chunk = 0
    for bit in range(CHUNK/BIT):
        sine_amplitude = 0.0
        cosine_amplitude = 0.0
        for i in range(BIT):
            cosine_amplitude += received_signal[ position_in_chunk ] * cosines[ position_in_chunk ] / BIT
            sine_amplitude += received_signal[ position_in_chunk ] * sines[ position_in_chunk ] / BIT
            position_in_chunk += 1

        mag = math.sqrt( cosine_amplitude**2 + sine_amplitude**2 ) * 1000
        theta = math.degrees( math.atan2( cosine_amplitude, sine_amplitude ) )


        # draw bit
        context.foreground = fg
        y_coor = (HEIGHT/2) + (cosine_amplitude) * (HEIGHT/2)
        x_coor = (WIDTH/2) + (sine_amplitude) * (WIDTH/2)

        pixmap.draw_rectangle(context, True, int(x_coor)-5, int(y_coor)-5, 10, 10 )

    # blit to screen
    drawable.draw_drawable( context, pixmap, 0, 0, 0, 0, -1, -1 )

#    print mag, theta
    return True

gobject.idle_add(capture_audio)
gtk.main()

stream.stop_stream()
stream.close()
p.terminate()
