import requests
import os
import random
import time
from threading import Thread
from multiprocessing import Process
import argparse

parser = argparse.ArgumentParser(description='--head,--qps,--node_size')
 
parser.add_argument('-head','--head', type=int, default=1)
parser.add_argument('-q','--qps', type=int, default=1200)
parser.add_argument('-n','--node_size', type=int, default=3)
parser.add_argument('-p','--process', type=int, default=20)
parser.add_argument('-d','--duration', type=int, default=35)
parser.add_argument('-t','--types', type=int, default=15)
parser.add_argument('-host','--host', type=str, default="http://10.107.37.224:5000/")

cg_rate_list_all=[  
                  [1,1,1,1,1,1,1,1], # 0
                  [1,0,0,0,0,0,0,0], # 1
                  [0,1,0,0,0,0,0,0], # 2
                  [0,0,1,0,0,0,0,0], # 3
                  [0,0,0,1,0,0,0,0], # 4
                  [0,0,0,0,1,0,0,0], # 5
                  [0,0,0,0,0,1,0,0], # 6
                  [0,0,0,0,0,0,1,0], # 7 readuserTimeline
                  [0,0,0,0,0,0,0,1], # 8 readhomeTimeline
                  [8,8,8,8,8,8,22,10], # 9 lab1
                  [11,11,11,11,11,11,7,7], # 10 lab2
                  [4,8,18,10,10,10,10,10], # 11 lab3
                  [4,8,18,6,13,11,10,10], # 12 lab4
                  [2,6,16,8,8,8,22,10], # 13 lab5
                  [7,9,17,11,11,11,7,7], # 14 lab6
                  [4,8,18,6,13,11,15,5], # 15 lab7
                  ]
cg_rate_list=[]
data="http://10.98.245.134:5000/"
node_list=['cpu-02','cpu-09','cpu-10']

#gaussian distribution
def generate_gaussian_arraival():
    dis_list=[]
    with open("/state/partition/jcshi/CJY/socialNetwork/System/GD_norm.csv") as f:
        for line in f:
            dis_list.append(float(line.replace("\n","")))
    return dis_list

#post a request
def post_request(url, params):
    response=requests.get(url=url,params=params,headers={'Connection':'close'},timeout=(50,50))
    # latencies.append(response.elapsed.total_seconds())

# generate requests with svc+CallGraph
def dynamic_graph_rate(dr1=1,dr2=1,dr3=1,dr4=1,dr5=1,dr6=1,dr7=1,dr8=1):
    coin=random.random()
    cnt=dr1+dr2+dr3+dr4+dr5+dr6+dr7+dr8
    coin*=cnt
    if(coin<dr1):
        url=data+"composePost"
        params={"cg":"1"}
    elif(coin<dr1+dr2):
        url=data+"composePost"
        params={"cg":"2"}
    elif(coin<dr1+dr2+dr3):
        url=data+"composePost"
        params={"cg":"3"}
    elif(coin<dr1+dr2+dr3+dr4):
        url=data+"composePost"
        params={"cg":"4"}   
    elif(coin<dr1+dr2+dr3+dr4+dr5):
        url=data+"composePost"
        params={"cg":"5"}
    elif(coin<dr1+dr2+dr3+dr4+dr5+dr6):
        url=data+"composePost"
        params={"cg":"6"}
    elif(coin<dr1+dr2+dr3+dr4+dr5+dr6+dr7):
        url=data+"readuserTimeline"
        params=None
    else:
        url=data+"readhomeTimeline"
        params=None
    return url, params

def threads_generation(QPS_list,duraion,process_number):
    plist = []
    dis_list = []
    gs_inter=generate_gaussian_arraival()
    for j in range(0,duraion):
        QOS_this_s=int(QPS_list[j]/process_num)
        for i in range(0,QOS_this_s):
            url, params=dynamic_graph_rate(cg_rate_list[0],cg_rate_list[1],
            cg_rate_list[2],cg_rate_list[3],cg_rate_list[4],cg_rate_list[5],cg_rate_list[6],cg_rate_list[7])
            p = Thread(target=post_request,args=(url,params))
            plist.append(p)
            dis_list.append(gs_inter[i%250]* 250/QOS_this_s)
    print("Total %d thread in %d s"%(len(dis_list),duraion))
    fun_sleep_overhead=0.000075# overhead to call sleep()function
    print("begin")
    waste_time=0
    t1=time.time()
    for i in range(len(plist)):
        t_s=time.time()#10^-3ms, negligible
        plist[i].start()
        t_e=time.time()
        sleep_time=dis_list[i]/1000-((t_e-t_s)+fun_sleep_overhead)
        if(sleep_time>0):
            # can compensate
            if(sleep_time+waste_time>=0):
                time.sleep(sleep_time+waste_time)
                waste_time=0
            else:
                waste_time+=sleep_time
        else:
            waste_time+=sleep_time
    t2=time.time()
    print("done, time count is %f,should be %d, waste_time %f\n"%(t2-t1,duraion,waste_time))
    for item in plist:
        item.join()

#similar to wrk
def request_test(QPS_list,duraion=20,process_number=20):
    time1=time.time()
    assert len(QPS_list)==int(duraion)
    process_list=[]
    for i in range(process_number):
        p=Process(target=threads_generation,args=(QPS_list,duraion,process_number))
        process_list.append(p)
    # start processes
    for p in process_list:
        p.start()
    print("All processes start.")
    for p in process_list:
        p.join()
    print("All processes done.")    
    print(time.time()-time1)

def run_on_node(cmd):
    os.system(cmd)

if __name__ == "__main__":
    args = parser.parse_args()
    
    if args.head:
        data = args.host
        o_process_list=[]
        for i in range(args.node_size):
            cmd=" ssh {} 'python3 /state/partition/jcshi/CJY/socialNetwork/System/LoadGenerator-new.py --head {} --qps {} --node_size {} -p {} -t {} -d {} -host {}' "\
                .format(node_list[i],0,args.qps,args.node_size,args.process,args.types,args.duration, data)
            print(cmd)
            # run_on_node(cmd)
            p=Process(target=run_on_node,args=(cmd,))
            o_process_list.append(p)
        for p in o_process_list:
            p.start()
        for p in o_process_list:
            p.join()
    else:
        print(args)
        data = args.host
        os.system("ulimit -n 100000")
        QPS=int(args.qps/args.node_size)
        duraion=args.duration
        process_num=args.process
        cg_rate_list=cg_rate_list_all[args.types]
        QPS_list=[]
        for i in range(duraion):
            QPS_list+=[QPS]
        print(QPS_list)
        request_test(QPS_list,duraion,process_num)