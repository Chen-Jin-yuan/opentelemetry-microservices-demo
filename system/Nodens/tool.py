import os
import numpy as np
import time
import requests
import json
import pandas
import datetime
import csv
from getlatency import getQueryData,latency_tot,latency_tot_new

ip_nodeName={
    "cpu-07":"10.2.64.7",
    "cpu-08":"10.2.64.8",
    "cpu-04":"10.2.64.4",
    "cpu-06":"10.2.64.6"
    # cpu-03 frontend 不需要改资源
}

def get_time_stamp16(inputTime):
    date_stamp = str(int(time.mktime(inputTime.timetuple())))
    data_microsecond = str("%06d"%inputTime.microsecond)
    date_stamp = date_stamp+data_microsecond
    return int(date_stamp)

def get_latency(startTs,endTs,period):
    data=requests.get(url='http://127.0.0.1:30911/api/traces?service=frontend&start='+str(startTs)+'&end='+str(endTs)+'&prettyPrint=true&limit=6000000').json()
    counter=0
    latency = []
    errorCount=0
    for element in data['data']:
        counter+=1
        spanCount=0
        minTs=0.0
        maxTs=0.0
        flag=1
        for a in element['spans']:
            for b in a['tags']:
                if(b['key']=="error" and b['value']==True):
                    flag=0
            if(flag==0):
                errorCount+=1
                break
            spanCount+=1
            if(spanCount==1):
                minTs=float(a['startTime'])
                maxTs=float(a['startTime'])+float(a['duration'])
            else:
                if(minTs>float(a['startTime'])):
                    minTs=float(a['startTime'])
                else:
                    minTs=minTs
                if(maxTs<(float(a['startTime'])+float(a['duration']))):
                    maxTs=float(a['startTime'])+float(a['duration'])
                else:
                    maxTs=maxTs
        if(flag==1):
            time=(maxTs-minTs)/1000
            latency.append(time)
    if(counter==0 or len(latency)==0):
        return [0,0,0,0,0,0]
    return [np.mean(latency),np.percentile(latency,50),np.percentile(latency,95),np.percentile(latency,99),len(latency)/period,errorCount]

def latency_analyze(startTime,duration):
    for svc in ["checkout", "browse","view","add"]:
        t_start=int(startTime*1000000)
        t_end=int((startTime+duration)*1000000)
        interval=100000#every 100ms requests
        index=t_start
        counter=0
        while(index<=t_end):
            # res=get_latency(index,index+interval,0.1)
            res=latency_tot_new(index,index+interval,svc,0.1)
            # print(svc,counter,index,index+interval,res[0],res[1],res[2],res[3],res[4])
            with open("results/latency-jaeger.csv", 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([svc,counter,index,index+interval,res[0],res[1],res[2],res[3],res[4]])
                #倒数第二个是99分为延迟
            index+=interval
            counter+=1

#内存使用量
def get_memory_usage(pod_uid,ip_str):
    cadvisor_url = "http://"+ip_str+":8090/api/v1.3/containers/kubepods/besteffort/"
    url = f"{cadvisor_url}{pod_uid}"
    response = requests.get(url)
    data = response.json()
    if data.get('stats', None) == None:
        return 0
    stats = data['stats']#['cpu']['usage']['total']#这里每次会取60个时间间隔,每两个间隔1.5s左右,只取最后两个间隔进行统计
    memory_usage=float(stats[-1]['memory']['usage'])/1000000
    return memory_usage

def montorMEM(pod_uids):
    for k,v in pod_uids.items():
        with open("data/MS_nodes_mapping.json","r") as json_file:
            pode_nodes=json.load(json_file)
        ip_str=ip_nodeName[pode_nodes[k][0].replace("\n","")]#对应node ip
        for vv in v:
            pod_uid="pod"+vv.replace("\n","")
            memory_usage_tot=get_memory_usage(pod_uid,ip_str)
            print("%20s %20s %10f" % (k,pod_uid,memory_usage_tot))
            with open("results/Memory.csv", 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([k,pod_uid,memory_usage_tot])

if __name__ == "__main__":
    # print(time.time())
    latency_analyze(1704306303.4187799,20)