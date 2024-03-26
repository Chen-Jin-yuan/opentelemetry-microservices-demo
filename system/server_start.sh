#!/bin/bash

# 节点列表
nodes=("cpu-03" "cpu-04" "cpu-07" "cpu-08")

# 服务器脚本路径
script_path="/home/jcshi/hotelReservations/System"

# 遍历节点列表
for node in "${nodes[@]}"
do
    echo "Connecting to $node..."
    
    # 使用 ssh 连接节点并执行命令
    ssh "$node" "cd $script_path && sudo python3 server.py" &
done

wait

echo "All servers started."
