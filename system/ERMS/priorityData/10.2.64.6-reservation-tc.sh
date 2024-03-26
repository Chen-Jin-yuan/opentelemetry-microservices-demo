# Config number of virtual interface
modprobe ifb numifbs=2
echo "Set numifbs to 2"
# Get container's network interface
echo "Working on container 3"
NET=`docker exec -i 4d098866f658 bash -c 'cat /sys/class/net/eth*/iflink'`
NET=`echo $NET|tr -d '\r'`
VETH=`grep -l $NET /sys/class/net/cali*/ifindex`
VETH=`echo $VETH|sed -e 's;^.*net/\(.*\)/ifindex$;\1;'`
VETH=`echo $VETH|tr -d '\r'`
echo "Get container's network interface OK"
# Create virtual interface
ip link delete ifb3
ip link add ifb3 type ifb
ip link set ifb3 up
echo "Create network virtual interface OK"
# Redirect to virtual interface
tc qdisc del dev $VETH handle ffff: ingress
tc qdisc add dev $VETH handle ffff: ingress
tc filter add dev $VETH parent ffff: \
    protocol ip u32 match u32 0 0 \
    flowid 1:1 action mirred egress redirect dev ifb3
echo "Add redirection OK"
# Add root
tc qdisc add dev ifb3 root handle 1:0 htb default 10
echo "Add root OK"
# Add classes
tc class add dev ifb3 parent 1:0 classid 1:1 htb prio 1 rate 10Mbit
tc filter add dev ifb3 protocol ip parent 1:0 u32 match ip src 10.244.145.130/32 flowid 1:1
tc class add dev ifb3 parent 1:0 classid 1:2 htb prio 0 rate 10Mbit
tc filter add dev ifb3 protocol ip parent 1:0 u32 match ip src 10.244.145.186/32 flowid 1:2
echo "Add classes OK"
# Get container's network interface
echo "Working on container 4"
NET=`docker exec -i 46853d7e5f1a bash -c 'cat /sys/class/net/eth*/iflink'`
NET=`echo $NET|tr -d '\r'`
VETH=`grep -l $NET /sys/class/net/cali*/ifindex`
VETH=`echo $VETH|sed -e 's;^.*net/\(.*\)/ifindex$;\1;'`
VETH=`echo $VETH|tr -d '\r'`
echo "Get container's network interface OK"
# Create virtual interface
ip link delete ifb4
ip link add ifb4 type ifb
ip link set ifb4 up
echo "Create network virtual interface OK"
# Redirect to virtual interface
tc qdisc del dev $VETH handle ffff: ingress
tc qdisc add dev $VETH handle ffff: ingress
tc filter add dev $VETH parent ffff: \
    protocol ip u32 match u32 0 0 \
    flowid 1:1 action mirred egress redirect dev ifb4
echo "Add redirection OK"
# Add root
tc qdisc add dev ifb4 root handle 1:0 htb default 10
echo "Add root OK"
# Add classes
tc class add dev ifb4 parent 1:0 classid 1:1 htb prio 1 rate 10Mbit
tc filter add dev ifb4 protocol ip parent 1:0 u32 match ip src 10.244.145.130/32 flowid 1:1
tc class add dev ifb4 parent 1:0 classid 1:2 htb prio 0 rate 10Mbit
tc filter add dev ifb4 protocol ip parent 1:0 u32 match ip src 10.244.145.186/32 flowid 1:2
echo "Add classes OK"
echo "Priority implemented"
