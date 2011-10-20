# Test file for PSet #3
import math
import numpy
import matplotlib.pyplot as p

#########################################################################
###            System Block Boxes (fast and slow)
#########################################################################

# Solves difference equation:
# yCoeffs[0]*y(n) + .. + yCoeffs[K]*y(n-K) =
#                 xCoeffs[0]*x(n) + + xCoeffs[L]*x(n-L)
# Uses initial conditions for y, y[n] = 0, n < 0, and assumes x[n] = 0, n < 0
def black_box(xin, yCoeffs, xCoeffs, pad=0):
    assert(len(yCoeffs) == len(xCoeffs))
    assert(yCoeffs[0] != 0.0)
    scale = 1.0/float(yCoeffs[0])
    yCoeffs = numpy.array(yCoeffs[1:])
    xCoeffs = numpy.array(xCoeffs)
    k = len(xCoeffs)
    x = numpy.zeros(k+1+len(xin))
    x[k+1:] = xin[:]
    y = numpy.zeros(len(x))
    for i in xrange(k+1,len(y)):
        xpast = numpy.inner(xCoeffs,x[i:i-k:-1])
        ypast = numpy.inner(yCoeffs,y[i-1:i-k:-1])
        y[i] = scale*(xpast - ypast)
    output = y[k+1:]
    return output

# Channel callable object.  The parameters of the channel are:
# channelid = '0' (fast channel),
#             '1' (very slow channel)
#             '2' (medium channel with ringing)
# noise = float > 0 is the amplitude of added channel noise.  Returns
# an instance which you can use like a function:
#   chan0 = channel(channelid='0',noise=0.0)
#   response = chan1(input)
# where input and response are sequences of floating point values
# (actually input is converted to a numpy array and response is
# a numpy array, but you can treat it like a list).
class channel:
    def __init__(self,channelid='0',noise=0.0,use_normal=False):
        self.id = channelid
        self.noise = noise
        self.use_normal = use_normal
        if self.id == '0' or self.id==0:
            self.den = [1,-0.4]
            self.num = [0.42, 0.0]
        elif self.id == '1' or self.id==1:
            self.den = [1,-2.7,2.43,-0.729]
            self.num = [0.0,0.0,0.0,0.001]
        elif self.id == '2' or self.id==2:
            self.den = [1, -2.0/3.0, 13/16.0]
            self.num = [5.0/16.0,0,0]
        else:
            assert False, "unknown channel %s" % self.id

    # a channel instance behaves like a function: call it with
    # a sequence of voltages representing the input; it returns
    # a sequence of voltages representing the response.
    def __call__(self,input):
        input = numpy.array(input)  # convert to numpy array
        out = black_box(input,self.den, self.num,0)
        if self.noise > 0:
            s = len(out)
            if self.use_normal:
                noisevals = numpy.random.normal(scale=self.noise,size=s)
            else:
                noisevals = numpy.random.triangular(-1,0,1,size=s)
                noisevals *= self.noise
            out = out + noisevals
        return out

def demo_deconvolve(input, mychannel, h, deconvolve):
    # Transmit the data through the channel
    rcvd = mychannel(numpy.append(input,numpy.zeros(len(h))))

    # Deconvolve the 
    deconv = deconvolve(rcvd,h)

    plots = [311,312,313]
    plotf = p.plot

    p.figure()
    p.subplots_adjust(hspace = 0.6)
    p.subplot(plots[0])
    plotf(input)
    p.title("Input Samples")
    p.subplot(plots[1])
    plotf(rcvd[0:len(input)])
    p.title("Received Samples")
    p.subplot(plots[2])
    d = deconv[0:len(input)]
    plotf(d)
    p.title("Deconvolved Samples")
    #p.ylim((max(min(d),-1e3),min(max(d),1e3)))

# for Task #1
def plot_USR(response,name):
    p.figure()
    p.stem(range(len(response)),response)
    smin = min(response)
    smax = max(response)
    ds = smax - smin
    p.axis([-.5,len(response)+.5,smin - 0.1*ds,smax + 0.1*ds])
    p.title('Response of channel %s' % name)
    p.xlabel('Sample number')
    p.ylabel('Voltage')

# transmit waveform, message is binary string or sequence
def transmit(message,samples_per_bit,v0=0,v1=1):
    s = [v0]*(samples_per_bit*len(message))
    for i in xrange(len(message)):
        if message[i] == '1' or message[i] == 1:
            j = i * samples_per_bit
            s[j:j + samples_per_bit] = [v1]*samples_per_bit
    return s


def testrun(channel,message,samples_per_bit=8,npreamble=0,npostamble=0,hlen=127):
    x = [0.0]*(npreamble + len(message)*samples_per_bit + npostamble)
    index = npreamble
    one_bit_samples = [1.0]*samples_per_bit
    for i in range(len(message)):
        next_index = index + samples_per_bit
        if message[i] == 1:
            x[index:next_index] = one_bit_samples
        index = next_index
    y = channel(x)
    h = channel([1.0]+hlen*[0.0])
    return (x,y,h)

def maxdiff(x,w):
    return max([abs(x[i]-w[i]) for i in xrange(min(len(w),len(x)))])

# convert digital sample sequence into voltages; result is numpy array.
# samples_per_bit can be a float (eg, 8.1) to model clock
# drift in the transmitter.
# NOTE JKW; NO DEFAULT VALUES FOR SAMPLES_PER_BIT, causes confusion
def bits_to_samples(bits,samples_per_bit,
                    npreamble=0,
                    npostamble=0,
                    v0 = 0.0,
                    v1 = 1.0,
                    repeat = 1):
    """ generate sequence of voltage samples:
          bits: binary message sequence
          npreamble: number of leading v0 samples
          npostamble: number of trailing v0 samples
          samples_per_bit: number of samples for each message bit
          v0: voltage to output for 0 bits
          v1: voltage to output for 1 bits
          repeat: how many times to repeat whole shebang
    """
    # Preallocate samples list and default to all v0's
    samples = [v0]*(npreamble + int(len(bits)*samples_per_bit) + npostamble)
    index = npreamble
    for i in xrange(len(bits)):
        if bits[i] != 0:
            start = int(index)
            end = int(index + samples_per_bit)
            samples[start:end] = [v1]*(end-start)
        index = index + samples_per_bit
    
    samples = samples * repeat

    return numpy.array(samples)

def test_deconvolve(deconvolver,channel,message):
    # send message through the channel
    x,y,h = testrun(channel,message)

    # deconvolve
    w = deconvolver(y,h)

    print "Using channel %s:" %channel.id,"the input and output of deconvolver differ by",maxdiff(x,w)

    # compute vertical axis bounds
    vmax = max(max(x),max(y),max(w))
    vmin = min(min(x),min(y),min(w))
    delta = vmax - vmin
    vmax += 0.1 * delta
    vmin -= 0.1 * delta

    p.figure()
    p.subplots_adjust(hspace=0.6)
    # plot input to channel
    p.subplot(3,1,1)
    p.plot(x)
    p.axis([-1,len(x)+1,vmin,vmax])
    p.xlabel('Sample number')
    p.ylabel('Volts')
    p.title('Input to channel %s' % channel.id)
    # plot output from channel
    p.subplot(3,1,2)
    p.plot(y)
    p.axis([-1,len(x)+1,vmin,vmax])
    p.xlabel('Sample number')
    p.ylabel('Volts')
    p.title('Output from channel %s' % channel.id)
    # plot deconvolved output
    p.subplot(3,1,3)
    p.plot(w)
    p.axis([-1,len(x)+1,vmin,vmax])
    p.xlabel('Sample number')
    p.ylabel('Volts')
    p.title('Deconvolved output from channel %s (noise=%g)' % (channel.id,channel.noise))

def verify_task5(f):
    points = 0
    m = [1,0,1,1,0,1,1,0,0,1,0,0]

    channel1 = channel.channel('1')
    x,y,h = testrun(channel1,m)
    w = f(y,h)
    if maxdiff(x,w) < 1e-3: points += 1.5

    channel2 = channel.channel('2')
    x,y,h = testrun(channel2,m)
    w = f(y,h)
    if maxdiff(x,w) < 1e-3: points += 1.5

    return points
