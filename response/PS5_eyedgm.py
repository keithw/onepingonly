# template for PSet #3, Python Task #1
import au_sendreceive
import numpy
import matplotlib
matplotlib.use('macosx')
import matplotlib.pyplot as p
import PS5_tests

def all_bit_patterns(n):
    # generate all possible n-bit bit sequences and merge into a single array
    message = [0] * (n * 2**n)
    for i in xrange(2**n):
        for j in xrange(n):
            message[i*n + j] = 1 if (i & (2**j)) else 0
    return numpy.array(message,dtype=numpy.int)

def plot_eye_diagram_fast(channel,plot_label, samples_per_bit):
    """
    Plot eye diagram for given channel using all possible 6-bit patterns
    merged together as message. plot_label is the label used in the eye
    diagram, Samples_per_bit determines how many samples
    are sent for each message bit.
    """

    # build message
    message = all_bit_patterns(6)
    
    # send it through the channel
    result = channel(lab1.bits_to_samples(message,samples_per_bit))

    # Truncate the result so length is divisible by 3*samples_per_bit
    result = result[0:len(result)-(len(result) % (3*samples_per_bit))]

    # Turn the result in to a n by 3*samples_per_bit matrix, and plot each row
    mat_samples = numpy.reshape(result,(-1,3*samples_per_bit))
    p.figure()
    p.plot(mat_samples.T)
    p.title('Eye diagram for channel %s' % plot_label)


def plot_eye_diagram(channel,plot_label, samples_per_bit):
    """
    Your, more educational, version of plot_eye_diagram.  For the
    given channel, you should generate a bit sequence made of all
    possible 3 bit messages (you can use the all_bit_patterns function
    above), and then plot the received samples by overlaying sets of
    3*samples_per_bit.  So that you can watch the eye diagram form,
    have the program stop for a press of enter after every
    3*samples_per_bit plot The python function raw_input('Press enter
    to continue') will help.
    """
    # Number of samples in a plot interval
    interval = 3*samples_per_bit

    # build message
    message = all_bit_patterns(3)
    
    # send it through the channel
    result = channel(PS5_tests.bits_to_samples(message,samples_per_bit))

    # Truncate the result so length is divisible by interval
    result = result[0:len(result)-(len(result) % interval)]

    # produce the eye diagram one line at a time, waiting for a key press
    p.figure()
    for i in range(0,len(result),3*samples_per_bit):
        p.plot(result[i:i+interval])
        raw_input("Press Enter to continue")

    # Finally add the title
    p.title('Eye diagram for channel %s' % plot_label)

if __name__ == '__main__':
    # Create the channels (noise free)
#    channel0 = PS5_tests.channel(channelid='0')
#    channel1 = PS5_tests.channel(channelid='1')
#    channel2 = PS5_tests.channel(channelid='2')
    auchan = au_sendreceive.channel()

    # plot the eye diagram for the three virtual channels
#    plot_eye_diagram(channel0,'0',samples_per_bit=50)
#    plot_eye_diagram(channel1,'1',samples_per_bit=50)
#    plot_eye_diagram(channel2,'2',samples_per_bit=50)
    plot_eye_diagram(auchan,'audio',samples_per_bit=4)

    p.show()
