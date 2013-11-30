#!/usr/bin/python
import os, socket, thread, time, argparse, sys
import termcolor as T

from re import search
from random import choice, shuffle
from subprocess import Popen, PIPE
from monitor import monitorFiles
from dht import DualHomedTop

from mininet.log import lg, setLogLevel
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.util import dumpNodeConnections, custom
from mininet.node import OVSKernelSwitch, RemoteController

from mptcp_util import enable_mptcp, reset, progress
from dctopo import FatTreeTopo, DualHomedTopo

def parse_args():
    parser = argparse.ArgumentParser(description="2-host n-switch test")
    parser.add_argument('-bw',
                        action="store",
                        help="Bandwidth of links",
                        default=10)
    parser.add_argument('-k',
                        action="store",
                        help="K for dual homed tree",
                        default=4)
    parser.add_argument('-sw',
                        action="store",
                        help="Number of switches.  Must be >= 1",
                        default=1)
    parser.add_argument('-ns',
                        action="store",
                        help="Number of senders.  Must be >= 1",
                        default=1)
    parser.add_argument('-nr',
                        action="store",
                        help="Number of receivers.  Must be >= 1",
                        default=1)
    parser.add_argument('-nflows',
                        action="store",
                        help="Set # subflows",
                        default=1)
    parser.add_argument('-ds',
                        action="store",
                        help="Dataset to use.",
                        default='covtype')
    parser.add_argument('-cs',
                        action="store",
                        help="Size of chunks to be used for...something.",
                        default=500)
    parser.add_argument('--mptcp',
                        action="store_true",
                        help="Enable MPTCP (net.mptcp.mptcp_enabled)",
                        default=False)
    parser.add_argument('--debug',
                        action="store_true",
                        help="Turn on debugging",
                        default=False)

    args = parser.parse_args()
    args.bw = int(args.bw)
    args.k = int(args.k)
    args.sw = int(args.sw)
    args.ns = int(args.ns)
    args.nr = int(args.nr)
    args.nflows = int(args.nflows)
    return args

def main():
    args = parse_args()
    pox_c = Popen("exec ~/pox/pox.py --no-cli riplpox.riplpox --topo=dht --routing=hashed --mode=reactive 1> /tmp/pox.out 2> /tmp/pox.out", shell=True)
    time.sleep(1) # wait for controller to start

    topo = DualHomedTopo(k=args.k)
    link = custom(TCLink, bw=args.bw)

    net = Mininet(controller=RemoteController, topo=topo, link=link, switch=OVSKernelSwitch)
    net.start()

    mappings = create_mappings(args, net)
    
    sndrs = mappings['s']
    rcvrs = mappings['r']

    # print 's:', sndrs
    # print 'r:', rcvrs

    # time.sleep(3)
    enable_mptcp(args.nflows)
    time.sleep(3)

    # sndrs[0].cmdPrint('ping -c1 %s' % rcvrs[0].IP())
    # net.pingAll()

    # pox_c.kill()
    # pox_c.wait()
    # return

    if args.debug:
        outfiles = {h: '/tmp/%s.out' % h.name for h in sndrs + rcvrs}
        errfiles = {h: '/tmp/%s.out' % h.name for h in sndrs + rcvrs}
        [ h.cmd('echo >',outfiles[h]) for h in sndrs + rcvrs ]
        [ h.cmd('echo >',errfiles[h]) for h in sndrs + rcvrs ]

        print outfiles
        print errfiles

    for r in rcvrs:
        if args.debug:
            r.sendCmd('python receiver.py --id %s --nr %d --ns %d --ds %s --debug'
                      % (r.name, args.nr, args.ns, args.ds),
                      '1>', outfiles[r],
                      '2>', errfiles[r])
        else:
            r.sendCmd('python receiver.py --id %s --nr %i --ns %i --ds %s' 
                      % (r, args.nr, args.ns, args.ds))

    time.sleep(1) # let servers start up

    ips = map(lambda x: x.IP(), rcvrs)

    for s,i in zip(sndrs,range(len(sndrs))):
        if args.debug:
            s.sendCmd('python sender.py --id %s --cs %d --ns %d --ips %s --ds %s --debug' 
                      % (i, args.cs, args.ns, ips, args.ds),
                      '1>', outfiles[s],
                      '2>', errfiles[s])
        else:
            s.sendCmd('python sender.py --id %s --cs %d --ns %d --ips %s --ds %s' %
                      (i, args.cs, args.ns, ips, args.ds))

    tts = {}
    ttr = {}
    for s in sndrs:
        tts[s] = s.waitOutput()
    for r in rcvrs:
        ttr[r] = r.waitOutput()

    print tts.values()
    print ttr.values()

    # kill pox controller
    pox_c.kill()
    pox_c.wait()
    
    net.stop()

    write_results(tts, ttr, args)

def write_results(tts, ttr, args):
    if not os.path.exists('../results'):
        os.makedirs('../results')

    if args.mptcp:
        f = open('../results/bw%s_sw%i_ns%i_nr_%i_nf%i_%s_mptcp.csv' %
                 (args.bw,args.sw,args.ns,args.nr,args.nflows,args.ds), 'w')
    else:
        f = open('../results/bw%s_sw%i_ns%i_nr_%i_nf%i_%s.csv' %
                 (args.bw,args.sw,args.ns,args.nr,args.nflows,args.ds), 'w')
    f.write('%s\n%s\n' %
            (','.join(map(lambda x: x.strip('\n'), tts.values())),
             ','.join(map(lambda x: x.strip('\n'), ttr.values()))))

    f.close()
    

def create_mappings(args, net):
    s_hosts = filter(lambda x: search('10\.[02468]\.\d\.\d',x.IP()), net.hosts)
    r_hosts = filter(lambda x: search('10\.[13579]\.\d\.\d',x.IP()), net.hosts)

    # shuffle(s_hosts)
    # shuffle(r_hosts)
    
    mappings = {'s' : [], 'r' : []}

    for s in range(args.ns):
        mappings['s'].append(s_hosts[s])

    for r in range(args.nr):
        mappings['r'].append(r_hosts[r])

    mappings['s'] = [ net.hosts[0] ]
    mappings['r'] = [ net.hosts[4] ]
    return mappings
    
if __name__ == '__main__':
    try:
        lg.setLogLevel('info')
        main()
    except:
        import traceback
        traceback.print_exc(file=sys.stdout)
        reset()
        os.system('cp /tmp/pox.out .')
        os.system("killall python2.7; mn -c; killall controller")
