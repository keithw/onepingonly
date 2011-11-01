# template for PSet #3, Python Task #1
import au_sendreceive
import numpy
import matplotlib
#matplotlib.use('macosx')
import matplotlib.pyplot as p
import PS5_tests

# arguments:
#   channel -- instance of the PS5_tests.channel class
#   max_length -- integer
#   tol -- float
# return value:
#   a voltage sequence of length max_length or less
def unit_step_response(channel,max_length=100):
    """
    Returns sequence of samples that corresponds to the unit-step
    response (USR) of the channel.

    channel is a function you call with an input sequence of voltage
    samples.  It returns a sequence of voltage values, which is the
    response of the channel to that input.
    
    max_length sets the length of the test waveform to be sent through
    the channel.

    """
#    step = [0]*(max_length*3/2) + [-1]*(max_length/2) + [1]*(max_length) + [-1]*(max_length/2) + [1]*(max_length/2) 
    step = [0] * 100 + [1] * 100 + [-1] * 100 + [0.5] * 100 + [-0.5] * 100
    step_response = channel(step)
#    return step_response[max_length/2 - 128: max_length/2 + 128]
    return step_response

if __name__ == '__main__':
    channel = au_sendreceive.channel( 1500, 500 )

    # plot the unit-sample response of our three virtual channels
#    PS5_tests.plot_USR(unit_step_response(channel0),'0')
#    PS5_tests.plot_USR(unit_step_response(channel1),'1')
#    PS5_tests.plot_USR(unit_step_response(channel2),'2')
    PS5_tests.plot_USR(unit_step_response(channel),'realaudio')

    p.show()
