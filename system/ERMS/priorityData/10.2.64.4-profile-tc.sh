# Config number of virtual interface
modprobe ifb numifbs=3
echo "Set numifbs to 3"
# Get container's network interface
echo "Working on container 0"
NET=`docker exec -i 5f29dfebbb90 bash -c 'cat /sys/class/net/eth*/iflink'`
NET=`echo $NET|tr -d '\r'`
VETH=`grep -l $NET /sys/class/net/cali*/ifindex`
VETH=`echo $VETH|sed -e 's;^.*net/\(.*\)/ifindex$;\1;'`
VETH=`echo $VETH|tr -d '\r'`
echo "Get container's network interface OK"
# Create virtual interface
ip link delete ifb0
ip link add ifb0 type ifb
ip link set ifb0 up
echo "Create network virtual interface OK"
# Redirect to virtual interface
tc qdisc del dev $VETH handle ffff: ingress
tc qdisc add dev $VETH handle ffff: ingress
tc filter add dev $VETH parent ffff: \
    protocol ip u32 match u32 0 0 \
    flowid 1:1 action mirred egress redirect dev ifb0
echo "Add redirection OK"
# Add root
tc qdisc add dev ifb0 root handle 1:0 htb default 10
echo "Add root OK"
# Add classes
tc class add dev ifb0 parent 1:0 classid 1:1 htb prio 1 rate 10Mbit
tc filter add dev ifb0 protocol ip parent 1:0 u32 match ip src 10.244.145.130/32 flowid 1:1
tc class add dev ifb0 parent 1:0 classid 1:2 htb prio 0 rate 10Mbit
tc filter add dev ifb0 protocol ip parent 1:0 u32 match ip src 10.244.145.137/32 flowid 1:2
echo "Add classes OK"
# Get container's network interface
echo "Working on container 1"
NET=`docker exec -i bad46762c954 bash -c 'cat /sys/class/net/eth*/iflink'`
NET=`echo $NET|tr -d '\r'`
VETH=`grep -l $NET /sys/class/net/cali*/ifindex`
VETH=`echo $VETH|sed -e 's;^.*net/\(.*\)/ifindex$;\1;'`
VETH=`echo $VETH|tr -d '\r'`
echo "Get container's network interface OK"
# Create virtual interface
ip link delete ifb1
ip link add ifb1 type ifb
ip link set ifb1 up
echo "Create network virtual interface OK"
# Redirect to virtual interface
tc qdisc del dev $VETH handle ffff: ingress
tc qdisc add dev $VETH handle ffff: ingress
tc filter add dev $VETH parent ffff: \
    protocol ip u32 match u32 0 0 \
    flowid 1:1 action mirred egress redirect dev ifb1
echo "Add redirection OK"
# Add root
tc qdisc add dev ifb1 root handle 1:0 htb default 10
echo "Add root OK"
# Add classes
tc class add dev ifb1 parent 1:0 classid 1:1 htb prio 1 rate 10Mbit
tc filter add dev ifb1 protocol ip parent 1:0 u32 match ip src 10.244.145.130/32 flowid 1:1
tc class add dev ifb1 parent 1:0 classid 1:2 htb prio 0 rate 10Mbit
tc filter add dev ifb1 protocol ip parent 1:0 u32 match ip src 10.244.145.137/32 flowid 1:2
echo "Add classes OK"
# Get container's network interface
echo "Working on container 2"
NET=`docker exec -i df8bbae267bc bash -c 'cat /sys/class/net/eth*/iflink'`
NET=`echo $NET|tr -d '\r'`
VETH=`grep -l $NET /sys/class/net/cali*/ifindex`
VETH=`echo $VETH|sed -e 's;^.*net/\(.*\)/ifindex$;\1;'`
VETH=`echo $VETH|tr -d '\r'`
echo "Get container's network interface OK"
# Create virtual interface
ip link delete ifb2
ip link add ifb2 type ifb
ip link set ifb2 up
echo "Create network virtual interface OK"
# Redirect to virtual interface
tc qdisc del dev $VETH handle ffff: ingress
tc qdisc add dev $VETH handle ffff: ingress
tc filter add dev $VETH parent ffff: \
    protocol ip u32 match u32 0 0 \
    flowid 1:1 action mirred egress redirect dev ifb2
echo "Add redirection OK"
# Add root
tc qdisc add dev ifb2 root handle 1:0 htb default 10
echo "Add root OK"
# Add classes
tc class add dev ifb2 parent 1:0 classid 1:1 htb prio 1 rate 10Mbit
tc filter add dev ifb2 protocol ip parent 1:0 u32 match ip src 10.244.145.130/32 flowid 1:1
tc class add dev ifb2 parent 1:0 classid 1:2 htb prio 0 rate 10Mbit
tc filter add dev ifb2 protocol ip parent 1:0 u32 match ip src 10.244.145.137/32 flowid 1:2
echo "Add classes OK"
echo "Priority implemented"
