# template for PSet #3, Python Task #1
import random
import sys
import au_sendreceive
import numpy
import matplotlib
matplotlib.use('macosx')
import matplotlib.pyplot as p
import PS5_tests
import PS5_usr_soln

# generate all possible b-bit bit sequences and merge into a single array
def all_bit_patterns(b):
    message = [0] * (b * 2**b)
    for i in xrange(2**b):
        for j in xrange(b):
            message[i*b + j] = 1 if (i & (2**j)) else 0
    return numpy.array(message,dtype=numpy.int)

# m random bit patterns of b bits
def rand_bit_patterns(b,m):
    message = [0] * (b * m)
    for i in xrange(m):
        for j in xrange(b):
            r = random.randint(0,1)
            message[i*b + j] = r
    return  numpy.array(message,dtype=numpy.int)

def plot_eye_diagram(channel,plot_label,hlen,samples_per_bit):
    """
    For the given channel, you should generate a bit sequence made of
    all possible B bit messages (you can use the all_bit_patterns
    function above), where B is picked using the formula B =
    floor(hlen/N) + 2.  Or, if B is too large (> 6, say), call
    rand_bit_patterns(B, 64).  Then plot the received samples by
    overlaying sets of 2*samples_per_bit + 1 samples.
    """
    # your code here

    B = hlen/samples_per_bit + 2
    # Number of samples in a plot interval
    interval = 2*samples_per_bit+1

    # build message
    if B < 7:
        message = all_bit_patterns(B)
    else:
#        print 'Too many bit patterns; increase samples_per_bit'
#        sys.exit(1)
        message = rand_bit_patterns(B,64)
    
    # send it through the channel
    result = channel(PS5_tests.bits_to_samples(message,samples_per_bit,v0=-1,v1=1))

    # Truncate the result so length is divisible by interval
    result = result[0:len(result)-(len(result) % interval)]

    # produce the eye diagram overlaid appropriately
    p.figure()
    for i in range(0,len(result),samples_per_bit):
        p.plot(result[i:i+interval])
#        raw_input("Press Enter to continue")

    # Finally add the title
    p.title('Eye diagram for channel %s' % plot_label)

def run_channel_eye(channel, id, samples_per_bit):
    l, unit_step_resp = PS5_usr_soln.unit_step_response(channel, wsize=20, tol=0.01)
    print 'Length of unit step response:', l
    plot_eye_diagram(channel,id,hlen=l,samples_per_bit=samples_per_bit)

if __name__ == '__main__':
    # Create the channels (noise free)
    """
    for i in range(0,3):
        print 'Software channel', i
        if i != 1:
            run_channel_eye(PS5_tests.channel(channelid=str(i)), str(i), 6)
        else:
            run_channel_eye(PS5_tests.channel(channelid=str(i)), str(i), 20)
"""
    # run acoustic channel and plot its eye diagram
    run_channel_eye(au_sendreceive.channel(), 'acoustic', samples_per_bit=50)

    p.show()
