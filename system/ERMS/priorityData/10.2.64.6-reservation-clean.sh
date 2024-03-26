NET=`docker exec -i 4d098866f658 bash -c 'cat /sys/class/net/eth*/iflink'`
NET=`echo $NET|tr -d '\r'`
VETH=`grep -l $NET /sys/class/net/cali*/ifindex`
VETH=`echo $VETH|sed -e 's;^.*net/\(.*\)/ifindex$;\1;'`
VETH=`echo $VETH|tr -d '\r'`
tc qdisc del dev $VETH handle ffff: ingress
ip link delete ifb3
NET=`docker exec -i 46853d7e5f1a bash -c 'cat /sys/class/net/eth*/iflink'`
NET=`echo $NET|tr -d '\r'`
VETH=`grep -l $NET /sys/class/net/cali*/ifindex`
VETH=`echo $VETH|sed -e 's;^.*net/\(.*\)/ifindex$;\1;'`
VETH=`echo $VETH|tr -d '\r'`
tc qdisc del dev $VETH handle ffff: ingress
ip link delete ifb4
