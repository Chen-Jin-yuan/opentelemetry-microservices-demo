import requests
import pandas as pd
import numpy as np
import json
import time
import os
import csv


def latency_tot_new(t_start,t_end,svc,period):
    marks={
        "browse":'http://127.0.0.1:30911/api/traces?operation=HTTP%20GET%20%2Fproduct&service=frontend&start='+str(int(t_start))+'&end='+str(int(t_end))+'&prettyPrint=true&limit=6000000',
        "view":'http://127.0.0.1:30911/api/traces?operation=HTTP%20GET%20%2Fcart%2Fview&service=frontend&start='+str(int(t_start))+'&end='+str(int(t_end))+'&prettyPrint=true&limit=6000000',
        "add":'http://127.0.0.1:30911/api/traces?operation=HTTP%20POST%20%2Fcart%2Fadd&service=frontend&start='+str(int(t_start))+'&end='+str(int(t_end))+'&prettyPrint=true&limit=6000000',
        "checkout":'http://127.0.0.1:30911/api/traces?operation=HTTP%20POST%20%2Fcart%2Fcheckout&service=frontend&start='+str(int(t_start))+'&end='+str(int(t_end))+'&prettyPrint=true&limit=6000000'
    }
    data=requests.get(url=marks[svc]).json()
    # print(data)
    # data=data.json()["data"]
    counter,flag,errorCount=0,1,0 #总请求数量\是否存现error_span\请求错误数量
    latency = list()
    # period=t_end-t_start#监测的时间周期
    for element in data['data']:
        counter+=1
        spanCount=0
        minTs,maxTs=0.0,0.0#最大时间和最小时间
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
    return [np.mean(latency),np.percentile(latency,50),np.percentile(latency,95),np.percentile(latency,99),len(latency)/period]

#分类获取query并记录
def getQueryData(t_start,t_end):
    # data_all=requests.get(url='http://127.0.0.1:30910/api/traces?service=frontend&start='+str(int(t_start*1000000))+'&end='+str(int(t_end*1000000))+'&prettyPrint=true&limit=6000000')
    # data_all=data_all.json()["data"]
    # with open('./latencyData/QueryData_all.json','w') as file:
    #     json.dump(data_all,file)
    data_search=requests.get(url='http://127.0.0.1:30910/api/traces?service=frontend&operation=HTTP%20GET%20%2Fhotels&start='+str(int(t_start*1000000))+'&end='+str(int(t_end*1000000))+'&prettyPrint=true&limit=6000000')
    data_search=data_search.json()["data"]
    with open('./latencyData/QueryData_search.json','w') as file:
        json.dump(data_search,file)
    data_user=requests.get(url='http://127.0.0.1:30910/api/traces?service=frontend&operation=HTTP%20GET%20%2Fuser&start='+str(int(t_start*1000000))+'&end='+str(int(t_end*1000000))+'&prettyPrint=true&limit=6000000')
    data_user=data_user.json()["data"]
    with open('./latencyData/QueryData_user.json','w') as file:
        json.dump(data_user,file)
    data_recommend=requests.get(url='http://127.0.0.1:30910/api/traces?service=frontend&operation=HTTP%20GET%20%2Frecommendations&start='+str(int(t_start*1000000))+'&end='+str(int(t_end*1000000))+'&prettyPrint=true&limit=6000000')
    data_recommend=data_recommend.json()["data"]
    with open('./latencyData/QueryData_recommend.json','w') as file:
        json.dump(data_recommend,file)
    data_reserve=requests.get(url='http://127.0.0.1:30910/api/traces?service=frontend&operation=HTTP%20POST%20%2Freservation&start='+str(int(t_start*1000000))+'&end='+str(int(t_end*1000000))+'&prettyPrint=true&limit=6000000')
    data_reserve=data_reserve.json()["data"]
    with open('./latencyData/QueryData_reserve.json','w') as file:
        json.dump(data_reserve,file)

#获取总latency,可以选择 all/search/recommend/user/reserve
def latency_tot(t_start,t_end,svc,mark=""):
    with open('./latencyData/QueryData_'+svc+'.json','r',encoding='utf-8') as file:
        json_string = file.read()
    data=json.loads(json_string)
    counter,flag,errorCount=0,1,0 #总请求数量\是否存现error_span\请求错误数量
    latency = list()
    period=t_end-t_start#监测的时间周期
    for element in data:
        counter+=1
        spanCount=0
        minTs,maxTs=0.0,0.0#最大时间和最小时间
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
    #Average\P50\P95\P99\Throughtput\error_per_second
    print(f'%60s %10f %10f %10f %10f %10f'%("Total_latency",np.mean(latency),np.percentile(latency,50),np.percentile(latency,95),np.percentile(latency,99),len(latency)/period))
    with open("./latencyData/"+mark+svc+".csv",mode='w',newline='',encoding='utf-8') as file:
        writer = csv.writer(file)
        row=["Total_latency",np.mean(latency),np.percentile(latency,50),np.percentile(latency,95),np.percentile(latency,99),len(latency)/period]#errorCount/period
        writer.writerow(row)
    return latency

#获取属于某个svc的ms的延迟数据(包含serviceName+operation或者只serviceName)
def latency_svc_ms(t_start,t_end,svc,mark=""):
    with open('./latencyData/QueryData_'+svc+'.json','r',encoding='utf-8') as file:
        json_string = file.read()
    data=json.loads(json_string)
    period=t_end-t_start
    # 存储每个serviceName+operationName 的调整后的延迟数据
    service_operation_adjusted_delays={}
    MS_delays={}
    # 计算调整后的延迟时间
    for request in data:
        span_durations={span["spanID"]: span["duration"] for span in request["spans"]}#存储每个span的时间
        child_spans={}# 存储每个span的子span
        for span in request["spans"]:
            for ref in span.get("references", []):
                if ref["refType"] == "CHILD_OF":
                    child_spans.setdefault(ref["spanID"], []).append(span["spanID"])
        temp_res={}
        for span in request["spans"]:
            service_name = request["processes"][span["processID"]]["serviceName"]
            operation_name = span["operationName"]
            key = service_name + ":" + operation_name
            span_id = span["spanID"]
            #!!!!!!这里暂时忽略了子级异步调用情况,目前这个benchmark中没有!!!!!!
            total_child_duration = sum(span_durations[child_id] for child_id in child_spans.get(span_id, []))
            adjusted_duration = max(span["duration"]-total_child_duration,0)
            if key not in service_operation_adjusted_delays:
                service_operation_adjusted_delays[key] = []
            service_operation_adjusted_delays[key].append(adjusted_duration/1000)
            #临时记录当前query每个span
            if(service_name in temp_res.keys()):
                temp_res[service_name]+=adjusted_duration/1000
            else:
                temp_res[service_name]=adjusted_duration/1000
        for k in temp_res.keys():#聚合同ms的span延迟,进行汇总记录
            if(k in MS_delays.keys()):
                MS_delays[k].append(temp_res[k])
            else:
                MS_delays[k]=[temp_res[k]]
    for key in service_operation_adjusted_delays.keys():
        latency=service_operation_adjusted_delays[key]
        print(f'%60s %10f %10f %10f %10f %10f'%(key,np.mean(latency),np.percentile(latency,50),np.percentile(latency,95),np.percentile(latency,99),len(latency)/period))
        with open("./latencyData/"+mark+svc+".csv",mode='a',newline='',encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([key,np.mean(latency),np.percentile(latency,50),np.percentile(latency,95),np.percentile(latency,99),len(latency)/period])
    for key in MS_delays.keys():
        latency=MS_delays[key]
        print(f'%60s %10f %10f %10f %10f %10f'%(key,np.mean(latency),np.percentile(latency,50),np.percentile(latency,95),np.percentile(latency,99),len(latency)/period))
        with open("./latencyData/"+mark+svc+".csv",mode='a',newline='',encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([key,np.mean(latency),np.percentile(latency,50),np.percentile(latency,95),np.percentile(latency,99),len(latency)/period])

if __name__ == "__main__":
    # t1=time.time()
    # os.system("./test.sh")#执行负载
    # t2=time.time()
    # print(t2-t1)
    # getQueryData(t1,t2)
    # latency_tot(t1,t2,"search")
    # latency_svc_ms(t1,t2,"search")
    # latency_tot(t1,t2,"user")
    # latency_svc_ms(t1,t2,"user")
    # latency_tot(t1,t2,"recommend")
    # latency_svc_ms(t1,t2,"recommend")
    # latency_tot(t1,t2,"reserve")
    # latency_svc_ms(t1,t2,"reserve")
    latency_tot_new(1703439931665736,1703439931765736,"reserve",0.1)
