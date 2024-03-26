#监控Ready_load+Wait_load+CallGraph比例
import json
import time
import csv
from Base import SVC_Shared, CG_Shared
from Graph import *

#获取5秒的load监控和CallGraph监控
def monitor_All():
    load_res=monitor_Ready_wait_one_time()
    graph_res_key,graph_res_number=graph_API()#监控graph,并且等同于sleep 5 seconds
    load_res=monitor_Ready_wait_one_time()
    #记录load+wait到文件
    with open("data/load_wait.json", 'w') as file:
            json.dump(load_res, file)
    #记录CallGraph number到文件
    with open("data/Recommend_CallGraphs_base.json", 'r') as file:
        data = json.load(file)
    for key,value in data.items():
        for i in range(len(graph_res_key)):
            if(set(value['mark'])==set(graph_res_key[i])):
                value['number']=graph_res_number[i]
    with open("data/Recommend_CallGraphs_base.json", 'w') as file:
        json.dump(data, file)
    #更新每个Call_Graph Shared Microservice的detailed_real_QPS和detailed_wait_QPS进行更新
    for sm in CG_Shared:
        sm.cal_detailed_QPS(data)
    record_QPS_oracle_real()
    
#这里就把所有微服务的real_QPS和wait_QPS进行了更新
def monitor_Ready_wait_one_time():
    res=dict()
    for sm in SVC_Shared:
        real_QPS,wait_QPS=sm.get_ready_waiting()
        # print(sm.msName,real_QPS,wait_QPS)
        this_dict=dict()
        this_dict['real']=real_QPS
        this_dict['wait']=wait_QPS
        res[sm.msName]=this_dict
    for sm in CG_Shared:
        real_QPS,wait_QPS=sm.get_ready_waiting()
        # print(sm.msName,real_QPS,wait_QPS)
        this_dict=dict()
        this_dict['real']=real_QPS
        this_dict['wait']=wait_QPS
        res[sm.msName]=this_dict
    return res

#一直定时监控,文件记录
def monitor_always():
    time_interval=1#每一秒监控一次
    while(True):
        t1=time.time()
        res=dict()
        for sm in SVC_Shared:
            real_QPS,wait_QPS=sm.get_ready_waiting()
            # print(sm.msName,real_QPS,wait_QPS)
            this_dict=dict()
            this_dict['real']=real_QPS
            this_dict['wait']=wait_QPS
            res[sm.msName]=this_dict
        with open("data/load_wait.json", 'w') as file:
            json.dump(res, file)
        t2=time.time()
        # print(t2-t1)
        time.sleep(1-(t2-t1))

def record_QPS_oracle_real():
    with open("data/scaling_configs.json", 'r') as file:
        data = json.load(file)
    for sm in SVC_Shared:
        real_QPS,wait_QPS=sm.return_read_waiting()        
        rows=list()
        for key in real_QPS.keys():
            rows.append([sm.msName,key,str(real_QPS[key]),str(data[sm.msName][key]['OracleQPS']),str(real_QPS[key]/data[sm.msName][key]['OracleQPS'])])    
        with open("results/monitor-QPS.csv", 'a', newline='') as file:
            writer = csv.writer(file)
            for row in rows:
                writer.writerow(row)
    for sm in CG_Shared:
        detailed_real_QPS,detailed_wait_QPS=sm.get_detailed_QPS()
        rows=list()
        for key in detailed_real_QPS.keys():
            couples=key.split(":")
            if(len(couples)==1):
                svc=key
                if data[sm.msName][svc]['OracleQPS'] == 1:
                    rows.append([sm.msName,svc,str(detailed_real_QPS[key]),str(data[sm.msName][svc]['OracleQPS']),"inf"])  
                else:
                    rows.append([sm.msName,svc,str(detailed_real_QPS[key]),str(data[sm.msName][svc]['OracleQPS']),str(detailed_real_QPS[key]/data[sm.msName][svc]['OracleQPS'])])    
            else:
                svc=key.split(":")[0]
                cg=key.split(":")[1]
                if data[sm.msName][svc][cg]['OracleQPS'] == 1:
                    rows.append([sm.msName,svc,cg,str(detailed_real_QPS[key]),str(data[sm.msName][svc][cg]['OracleQPS']),"inf"])  
                else:
                    rows.append([sm.msName,svc,cg,str(detailed_real_QPS[key]),str(data[sm.msName][svc][cg]['OracleQPS']),str(detailed_real_QPS[key]/data[sm.msName][svc][cg]['OracleQPS'])])      
        with open("results/monitor-QPS.csv", 'a', newline='') as file:
            writer = csv.writer(file)
            for row in rows:
                writer.writerow(row)