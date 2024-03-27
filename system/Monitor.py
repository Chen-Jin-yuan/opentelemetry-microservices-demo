#监控Ready_load+Wait_load+CallGraph比例
import json
import time
import csv
from Base import SVC_Shared

#获取5秒的load监控和CallGraph监控
def monitor_All():
    load_res=monitor_Ready_wait_one_time()
    time.sleep(5)#sleep 5 seconds
    load_res=monitor_Ready_wait_one_time()
    #记录load+wait到文件
    with open("data/load_wait.json", 'w') as file:
            json.dump(load_res, file)

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
            # 循环调用会导致计数多若干倍，可以提前预设一个文件统计每个service会循环调用几次，然后放缩
            # 这里使用简单的方式，直接用 OracleQPS
            print(key, sm.msName, sm.real_QPS[key], "->", data[sm.msName][key]['OracleQPS'])
            sm.real_QPS[key] = data[sm.msName][key]['OracleQPS']
        with open("results/monitor-QPS.csv", 'a', newline='') as file:
            writer = csv.writer(file)
            for row in rows:
                writer.writerow(row)