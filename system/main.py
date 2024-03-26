import multiprocessing
import time
from multiprocessing import Process
import os
import requests
from post_and_get import get_counter, get_svc_config

from Base import *
from Monitor import *
from Scaling import *
from tool import latency_analyze, montorMEM

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

    #初始化所有共享
    SVC_Shared=init_MSs()#SVC_shared: user reservation # CG_shared: dis price score profile
    print_all_sharedMSs("initialization")

    #设置初始横纵向拓展资源(实验初始状态): 只需要确定纵向, 横向和分组一开始手动计算设定
    initialize_MSs_states()

    #开始新的动态负载
    t_start=time.time()
    duration=20#预计执行实验时间
    # loadGenerator
    p_load = Process(target=load_func, args=())

    p_load.start()
    time.sleep(5) #等待4秒钟(LoadGenerator启动需要时间) or more?可以尝试一下
    
    #监测负载+CallGraph比例
    tt1=time.time()
    monitor_All()#获取5秒的load监控和CallGraph监控(所有监控数据获得)
    print_all_sharedMSs("monitoring")
    tt2=time.time()
    print("Monitoring Time=",tt2-tt1)
    
    # 停一下: 看一下monitor是不是准,如果不准(Nodens执行阻塞), 乘个数

    # profile 线性模型 # load -> 线性模型 # load-> oracle values
    # Scaling横纵向决策(根据monitor的记录)

    # Scaling_Decisions()
    
    # time.sleep(10)

    # try:
    #     montorMEM(pod_uids)
    # except:
    #     pass

    # 等待load执行结束,最终调整并记录
    p_load.join()
    
    latency_analyze(t_start,duration)#最后的param代表实验组号码

    # ip = nginxIP[0].replace("\n","")
    # url_c = f"http://{ip}:10001/counter"
    # get_counter(url_c)
