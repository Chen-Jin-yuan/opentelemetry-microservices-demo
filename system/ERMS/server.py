import time
from concurrent import futures
import grpc
import os
import distributed_pb2_grpc,distributed_pb2
from datetime import datetime,timedelta
_ONE_DAY_IN_SECONDS = 60 * 60 * 24

#1代表0.1CPU cores
def set_cpu(uids,cpu):
    cpu=int(cpu*10000)
    cpu_every=int(cpu/len(uids))
    for uid in uids:
        uid=uid.replace("\n","")
        path = '/sys/fs/cgroup/cpu/kubepods/besteffort/pod' + uid + '/cpu.cfs_quota_us'
        print(path,cpu_every)
        if cpu_every<1000:
            cpu_every=1000
        curr_value = str(cpu_every)
        with open(path, "w+") as f:
            f.write(curr_value)

#1代表100mb内存
def set_memory(uids,mem):
    mem=int(mem*100000000)
    mem_every=int(mem/len(uids))
    for uid in uids:
        uid=uid.replace("\n","")
        path = '/sys/fs/cgroup/memory/kubepods/besteffort/pod' + uid + '/memory.limit_in_bytes'
        print(path,mem_every)
        if mem_every<10000000:
            mem_every=10000000
        curr_value = str(mem_every)
        with open(path, "w+") as f:
            f.write(curr_value)

class TestService(distributed_pb2_grpc.GrpcServiceServicer):
    def __init__(self):
        pass
    
    # For adjusting resources (CPU/MEM)
    def adjustResCPU(self,request,context):
        uids=request.uids
        cpu_value=float(request.value)
        print(uids,cpu_value)
        set_cpu(uids,cpu_value)
        result='1'
        return distributed_pb2.ResResponse(result=str(result))
    def adjustResMEM(self,request,context):
        uids=request.uids
        mem_value=float(request.value)
        print(uids,mem_value)
        set_memory(uids,mem_value)
        result='1'
        return distributed_pb2.ResResponse(result=str(result))

#start server
def run():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=70))
    distributed_pb2_grpc.add_GrpcServiceServicer_to_server(TestService(),server)
    server.add_insecure_port('[::]:50052')
    server.start()
    print("start service...")
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    run()