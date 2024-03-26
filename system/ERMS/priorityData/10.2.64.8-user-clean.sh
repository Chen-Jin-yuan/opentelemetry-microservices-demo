NET=`docker exec -i ffa6ef9e7125 bash -c 'cat /sys/class/net/eth*/iflink'`
NET=`echo $NET|tr -d '\r'`
VETH=`grep -l $NET /sys/class/net/cali*/ifindex`
VETH=`echo $VETH|sed -e 's;^.*net/\(.*\)/ifindex$;\1;'`
VETH=`echo $VETH|tr -d '\r'`
tc qdisc del dev $VETH handle ffff: ingress
ip link delete ifb5
NET=`docker exec -i c3f905cf3dcb bash -c 'cat /sys/class/net/eth*/iflink'`
NET=`echo $NET|tr -d '\r'`
VETH=`grep -l $NET /sys/class/net/cali*/ifindex`
VETH=`echo $VETH|sed -e 's;^.*net/\(.*\)/ifindex$;\1;'`
VETH=`echo $VETH|tr -d '\r'`
tc qdisc del dev $VETH handle ffff: ingress
ip link delete ifb6
