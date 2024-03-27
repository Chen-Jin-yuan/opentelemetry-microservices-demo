import time
import json
from multiprocessing import Process,Manager
from NodensBase import SVC_Shared

def Scaling_Decisions(t_queue):
    # HorizontalOver(t_queue)#先做横向,其中包含了在横向具体action之前的借用资源纵向
    # time.sleep(1)
    Horizontal()
    OverProvision(t_queue)
    Vertical_back()

def run_func(i,this_new_num):
    SVC_Shared[i].horizontal_actions(this_new_num)

def HorizontalOver(t_queue):
    with open("data/scaling_configs.json", 'r') as file:
        data = json.load(file)
    with open("data/initialScaling.json",'r') as file:
        data2=json.load(file)
    SVC_Shared_new_nums=list()
    for sm in SVC_Shared:
        print("==============================Horizontal "+sm.msName+" ==============================")
        configs=data[sm.msName]
        min_load=10000
        tot_QPS=0
        for svc in configs.keys():
            if("max_load" in configs[svc]):
                if(configs[svc]["max_load"]<min_load):
                    min_load=configs[svc]["max_load"]
                tot_QPS+=configs[svc]["OracleQPS"]
            else:
                for cg in configs[svc].keys():
                    if(configs[svc][cg]["max_load"]<min_load):
                        min_load=configs[svc][cg]["max_load"]
                    tot_QPS+=configs[svc][cg]["OracleQPS"]
        replica_nums=max(int(tot_QPS/min_load)+1,2)
        over_replica=int((replica_nums-data2[sm.msName]["replicas"])*(time.time()-t_queue)/10)+1
        replica_nums+=over_replica
        print(sm.msName,min_load,tot_QPS,replica_nums)
        SVC_Shared_new_nums.append(replica_nums)
    process_list=[]
    for i in range(len(SVC_Shared)):
        this_new_num=SVC_Shared_new_nums[i]
        p=Process(target=run_func,args=(i,this_new_num))
        process_list.append(p)
    for p in process_list:
        p.start()
    for p in process_list:
        p.join() 


def Horizontal():
    with open("data/scaling_configs.json", 'r') as file:
        data = json.load(file)
    SVC_Shared_new_nums=list()
    for sm in SVC_Shared:
        print("==============================Horizontal "+sm.msName+" ==============================")
        configs=data[sm.msName]
        min_load=10000
        tot_QPS=0
        for svc in configs.keys():
            if("max_load" in configs[svc]):
                if(configs[svc]["max_load"]<min_load):
                    min_load=configs[svc]["max_load"]
                tot_QPS+=configs[svc]["OracleQPS"]
            else:
                for cg in configs[svc].keys():
                    if(configs[svc][cg]["max_load"]<min_load):
                        min_load=configs[svc][cg]["max_load"]
                    tot_QPS+=configs[svc][cg]["OracleQPS"]
        replica_nums=max(int(tot_QPS/min_load)+1,2) # 
        print(sm.msName,min_load,tot_QPS,replica_nums)
        SVC_Shared_new_nums.append(replica_nums)
    process_list=[]
    for i in range(len(SVC_Shared)):
        this_new_num=SVC_Shared_new_nums[i]
        p=Process(target=run_func,args=(i,this_new_num))
        process_list.append(p)
    for p in process_list:
        p.start()
    for p in process_list:
        p.join() 

def OverProvision(t_queue):#t_queue: 开始排队的时间
    with open("data/scaling_configs.json", 'r') as file:
        data=json.load(file)
    with open("data/initialScaling.json",'r') as file:
        data2=json.load(file)
    for sm in SVC_Shared:
        print("==============================OverProvision "+sm.msName+" ==============================")
        tot_resources=data[sm.msName+"-VerticalAll"]
        tot_resources_enlarge=tot_resources
        initial_resources=data2[sm.msName]["totRES"]
        sub_resources=tot_resources_enlarge-initial_resources
        over_resources=sub_resources*(time.time()-t_queue)/10
        tot_over_resources=tot_resources_enlarge+over_resources
        print("Actual, Enlarge, OverProvision RES",tot_resources,tot_resources_enlarge,tot_over_resources)
        sm.vertical_actions(tot_over_resources,"type:OVER-PROV")
    time.sleep(10)#排空资源10秒

def Vertical_back():
    with open("data/scaling_configs.json", 'r') as file:
        data = json.load(file)
    for sm in SVC_Shared:
        print("==============================VerticalBack "+sm.msName+" ==============================")
        tot_resources=data[sm.msName+"-VerticalAll"]
        print("Actual and Allocate RES",tot_resources,tot_resources)
        tot_resources=tot_resources
        sm.vertical_actions(tot_resources,"type:NORMAL")