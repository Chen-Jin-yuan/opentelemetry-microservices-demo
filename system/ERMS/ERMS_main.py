import os
import multiprocessing
import time
from multiprocessing import Process

from applyPriority import SetupShared,clear_vifs
from ERMSBase import *
from Scaling import Scaling_Decisions,Horizontal
from tool import latency_analyze,montorMEM
from scp_file import scp_to

# load generator copy to node
node_list=['cpu-02','cpu-09', 'cpu-10']#根据具体情况修改
# 同步文件
scp_to(node_list)

# nginxIP=os.popen("kubectl get pods -o wide | grep frontend | awk '{print $6}'").readlines()
# # 按顺序
# nginxIP = sorted(nginxIP)
nginxIP=os.popen("kubectl get svc | grep nginx | awk '{print $3}'").readlines()
frontend_host = "http://"+nginxIP[0].replace("\n","")+":5000/"
load_qps = 1600

def load_func():
    global frontend_host
    global load_qps
    os.system(f"python3 LoadGenerator-new.py -q {load_qps} -host {frontend_host}")

if __name__ == "__main__":
    #初始化微服务,横向+纵向拓展
    init_MSs()
    # init 在缩副本可能有问题，最好跑完一组重启所有pod
    initialize_MSs_states()

    # #首先设定3个固定共享微服务的优先级
    # # SetupShared()

    #开始新的动态负载
    t_start=time.time()
    duration=35#预计执行实验时间
    # loadGenerator
    p_load = Process(target=load_func, args=())
    p_load.start()
    time.sleep(5.5)#等待4秒钟(LoadGenerator启动需要时间),可能需要更短,我们的和baselines要设置同样

    #模拟执行监控,假设baseline监控完全准确
    time.sleep(5.5)#多出来的1在执行记录结果\输出等,为了保证对比公平需要全部相等
    #使用Profiling出来的值进行资源更新
    Scaling_Decisions()
    
    
    
    #休眠10秒后,将内存使用数据取出来
    time.sleep(10)

    try:
        montorMEM(pod_uids)
    except:
        pass

    # 等待load执行结束,最终调整并记录
    p_load.join()
    latency_analyze(t_start,duration)#最后的param代表实验组号码

    #实验完成后clear掉优先级
    # clear_vifs("priorityData")
    