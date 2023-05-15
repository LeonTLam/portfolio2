from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import TCLink


class LinuxRouter( Node ):
    """A Node with IP forwarding enabled.
    Means that every packet that is in this node, comunicate freely with its interfaces."""

    def config( self, **params ):
        super( LinuxRouter, self).config( **params )
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( LinuxRouter, self ).terminate()


class NetworkTopo( Topo ):

    def build( self, **_opts ):		
        h1=self.addHost("h1",ip=None)
        r2=self.addNode("r2",cls=LinuxRouter,ip=None)
        h3=self.addHost("h3",ip=None)
        self.addLink(h1,r2,params1={ 'ip' : '10.0.0.1/24' },params2={ 'ip' : '10.0.0.2/24' }, bw=100, delay='6.25ms')#,max_queue_size=834, use_htb=True)
        self.addLink(r2,h3,params1={ 'ip' : '10.0.1.1/24' },params2={ 'ip' : '10.0.1.2/24' }, bw=100, delay='6.25ms', max_queue_size=170)#, max_queue_size=834, use_htb=True)

topo = NetworkTopo()
net = Mininet( topo=topo, link=TCLink )
net.start()

#ip route add ipA via ipB dev INTERFACE
#every packet going to ipA must first go to ipB using INTERFACE
net["h1"].cmd("ip route add 10.0.1.2 via 10.0.0.2 dev h1-eth0")
net["h3"].cmd("ip route add 10.0.0.1 via 10.0.1.1 dev h3-eth0")
#this command is just to r3 ping r2 work, because it will use the correct ip
net["h3"].cmd("ip route add 10.0.0.2 via 10.0.1.1 dev h3-eth0")


net["h1"].cmd("ethtool -K h1-eth0 tso off")
net["h1"].cmd("ethtool -K h1-eth0 gso off")
net["h1"].cmd("ethtool -K h1-eth0 lro off")
net["h1"].cmd("ethtool -K h1-eth0 gro off")
net["h1"].cmd("ethtool -K h1-eth0 ufo off")


net["h3"].cmd("ethtool -K h3-eth0 tso off")
net["h3"].cmd("ethtool -K h3-eth0 gso off")
net["h3"].cmd("ethtool -K h3-eth0 lro off")
net["h3"].cmd("ethtool -K h3-eth0 gro off")
net["h3"].cmd("ethtool -K h3-eth0 ufo off")

net.pingAll()
CLI( net )
net.stop()
