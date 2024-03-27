import os
import multiprocessing
import time
from multiprocessing import Process

from NodensBase import *
from Scaling import Scaling_Decisions
from tool import latency_analyze,montorMEM
from scp_file import scp_to

# load generator copy to node
node_list=['cpu-02','cpu-09', 'cpu-10']#根据具体情况修改
# 同步文件
scp_to(node_list)

nginxIP=os.popen("kubectl get pods -o wide | grep frontend | awk '{print $6}'").readlines()
print(nginxIP)
frontend_host = "http://"+nginxIP[0].replace("\n","")+":8080/"
load_qps = 3000
load_type = 1
    

def load_func():
    global frontend_host
    global load_qps
    global load_type
    os.system(f"python3 LoadGenerator-dis-hr-new.py -q {load_qps} -host {frontend_host} -t {load_type} -d {duration}")

if __name__ == "__main__":

    #初始化微服务,横向+纵向拓展
    init_MSs()
    initialize_MSs_states()

    #开始新的动态负载
    t_start=time.time()
    duration=20#预计执行实验时间
    # loadGenerator
    p_load = Process(target=load_func, args=())
    p_load.start()

    time.sleep(5)#等待5秒钟(LoadGenerator启动需要时间),可能需要更短,我们的和baselines要设置同样
    t_queue=time.time()
    #模拟执行监控,假设baseline监控完全准确
    time.sleep(5.1)#多出来的1在执行记录结果\输出等,为了保证对比公平需要全部相等

    #使用Profiling出来的值进行资源更新,包含overprovision资源
    Scaling_Decisions(t_queue)

    # 等待load执行结束,最终调整并记录
    p_load.join()
    latency_analyze(t_start,duration)#最后的param代表实验组号码

    try:
        montorMEM(pod_uids)
    except:
        print("monitor mem failed")
