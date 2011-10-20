# template for PSet #3, Python Task #1
import au_sendreceive
import numpy
import matplotlib
matplotlib.use('macosx')
import matplotlib.pyplot as p
import PS5_tests

def unit_step_response(channel,max_length=100):
    step = [0] * 64 + [1] * 256 + [0] * 256 + [-1] * 256
    step_response = channel(step)
#    return step_response[max_length/2 - 128: max_length/2 + 128]
    return step_response


# arguments:
#   channel -- instance of the PS5_tests.channel class
#   max_length -- integer
#   tol -- float
# return value:
#   a voltage sequence of length max_length or less
def unit_step_response(channel,wsize=20,tol=0.01):
    """
    Returns sequence of samples that corresponds to the unit-step
    response (USR) of the channel.

    channel is a function you call with an input sequence of voltage
    samples.  It returns a sequence of voltage values, which is the
    response of the channel to that input.
    
    max_length sets the length of the test waveform to be sent through
    the channel.
    """
    input = [0] * 64 + [1] * 256 + [0] * 256 + [-1] * 256
    input = [-1] * 256 + [1] * 256
    # your code here
    response = channel(input)
    for i in xrange(256,len(response)):
        window = response[i:i+wsize]
        mean = numpy.mean(window)
        if mean > 1e-8 and numpy.std(window)/mean < tol:
            return len(response[256:i+wsize]), response
    return len(response), response

def run_channel(channel, id):
    l, unit_step_resp = unit_step_response(channel, wsize=20, tol=0.01)
    print 'Length of unit step response:', l
    PS5_tests.plot_USR(unit_step_resp,id)

if __name__ == '__main__':
    for i in range(0,3):
        print 'Software channel', i
        run_channel(PS5_tests.channel(channelid=str(i)), str(i))

    run_channel(au_sendreceive.channel(), 'acoustic')
    p.show()
