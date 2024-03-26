import requests
import json
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
import networkx as nx
import hashlib
import os
from multiprocessing import Process

def get_CallGraph(tracing_data):
    G_call=dict()
    service_names = {pid: data["serviceName"] for pid, data in tracing_data["processes"].items()}
    for span in tracing_data["spans"]:
        span_id = span["spanID"]
        process_id = span["processID"]
        service_name = service_names.get(process_id, "Unknown")  # 获取 serviceName
        operation_name = span["operationName"]
        node_label = service_name + ":" + operation_name  # 组合 serviceName 和 operationName
        if(node_label not in G_call.keys()):
            G_call[node_label]=1
        else:
            G_call[node_label]+=1
    return G_call

def are_graphs_equal(G1, G2):
    if(len(G1.keys())!=len(G2.keys())):
        return False
    for key in G1.keys():
        if(key not in G2.keys()):
            return False
    return True

classified_graphs = []
def classifed(tracing_data_all):
    counter=0
    t1=time.time()
    for tracing_data in tracing_data_all:
        if(not is_request_complete(tracing_data)):
            counter+=1
            continue
        G_call=get_CallGraph(tracing_data)
        already_classified = False
        for group in classified_graphs:
            if are_graphs_equal(G_call, group[0]):
                group.append(G_call)
                already_classified = True
                break
        if not already_classified:
            classified_graphs.append([G_call])
    t2=time.time()
    print("Data_classfied=",t2-t1)
    return counter#没有生成全的span

#判断获取到的某个请求是否已经完全生成
def is_request_complete(tracing_data):
    # 检查是否有根 span（没有父 span 的 span）
    root_span_found = any('references' not in span or len(span['references']) == 0 for span in tracing_data['spans'])
    # 检查所有 span 是否有开始和结束时间戳
    timestamps_complete = all('startTime' in span and 'duration' in span for span in tracing_data['spans'])
    # 检查每个非根 span 是否有有效的父 span 引用
    # valid_references = all(any(ref['refType'] == 'CHILD_OF' for ref in span['references']) if 'references' in span else True for span in tracing_data['spans'])
    return root_span_found and timestamps_complete

res_key,res_number=list(),list()#标记图和数字

def graph_API():
    global res_key,res_number
    tracing_data_all=list()
    res_key,res_number=list(),list()#标记图和数字
    ts=time.time()
    for i in range(1,6):
        tt1=time.time()
        t1=time.time()
        data=requests.get(url='http://127.0.0.1:30915/api/traces?service=nginx&start='+str(int((ts+i-4)*1000000))+'&end='+str(int((ts+i-3)*1000000))+'&prettyPrint=true&limit=60000')#每一秒拿一次数据
        t2=time.time()
        print("API_get_Data=",t2-t1)
        tracing_data_all=data.json()["data"]
        classifed(tracing_data_all)
        tt2=time.time()
        if(ts+i-2>time.time()):#下一个要取的时间段仍然比目前的时刻大
            time.sleep(ts+i-2-time.time())
        else:
            if(1-(tt2-tt1)>0):
                time.sleep(1-(tt2-tt1))
    total,index=0,0
    print(f"%5s %5s %8s"%("Graph","Nodes","Counts"))
    for cg in classified_graphs:
        index+=1
        total+=len(cg)
        print(f"%5d %5d %8d"%(index,len(cg[0].keys()),len(cg)))
        # print(list(cg[0].keys()))
        res_key.append(list(cg[0].keys()))
        res_number.append(len(cg))
    print("Total Queries=",total)
    return res_key,res_number


if __name__ == "__main__":
    res_key,res_number=graph_API()
    print(res_key)