import os
import time
import json
import grpc
import distributed_pb2_grpc
import distributed_pb2

#hardcode ips of nodes
ip_nodeName={
    "cpu-07":"10.2.64.7",
    "cpu-08":"10.2.64.8",
    "cpu-04":"10.2.64.4",
    "cpu-06":"10.2.64.6"
    # cpu-03 frontend 不需要改资源
}

#1代表0.1CPU cores
def rpc_set_cpu(node_name,uid_list,cpu):
    ip_str=ip_nodeName[node_name]+":50052"
    conn=grpc.insecure_channel(ip_str)
    client = distributed_pb2_grpc.GrpcServiceStub(channel=conn)
    request = distributed_pb2.ResRequest(uids=uid_list,value=cpu)
    response = client.adjustResCPU(request)
    return response.result
    print("Adjust CPU func received:",response.result)

#1代表100mb内存
def rpc_set_memory(node_name,uid_list,mem):
    ip_str=ip_nodeName[node_name]+":50052"
    conn=grpc.insecure_channel(ip_str)
    client = distributed_pb2_grpc.GrpcServiceStub(channel=conn)
    request = distributed_pb2.ResRequest(uids=uid_list,value=mem)
    response = client.adjustResMEM(request)
    return response.result
    print("Adjust MEM func received:",response.result)

# if __name__ == "__main__":
