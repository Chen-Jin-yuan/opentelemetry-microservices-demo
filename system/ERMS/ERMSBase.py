import requests
import json
import os
import copy
import time
import csv

from kubernetes import client, config
from AdjustRes import rpc_set_cpu, rpc_set_memory

config.load_kube_config()
v1 = client.CoreV1Api()
apps_v1_api = client.AppsV1Api()
scale = client.V1Scale()
namespace="default"#应用部署使用的命名空间
SVC_Shared=list()
MS_node_mapping=dict()
pod_uids=dict()#记录msName和uids的对应关系,为最后拿内存使用提供便利

#为了应对横向拓展之后所有的pod已经启动
def wait_for_pods_running(namespace="default", timeout=120):
    end_time = time.time() + timeout
    time.sleep(0.5)#监测间隔500ms
    wait_time=0.5
    while time.time() < end_time:
        pods = v1.list_namespaced_pod(namespace)
        all_running = True
        for pod in pods.items:
            if not (pod.status.phase == "Running" or pod.status.phase == "Terminating"):
                all_running = False
                break
        if all_running:
            print("All pods are in the Running state. Wait time=",wait_time)
            return True
        else:
            time.sleep(0.5)#监测间隔500ms
            wait_time+=0.5
    print("Timed out waiting for pods to be in the Running state.")
    return False

class SharedMS:

    def __init__(self,msName):
        self.msName=msName
        self.pods=list()
        self.IPs=list()
        self.replicaNumber=0
        self.uids=list()#用于进行资源分配

    def get_my_pods_ips(self):
        self.pods,self.IPs,self.replicaNumber,self.uids=[],[],0,[]
        deployment_name=self.msName
        pods_all = v1.list_namespaced_pod(namespace)
        for pod in pods_all.items:
            if pod.metadata.labels.get('io.kompose.service') == deployment_name:
                self.replicaNumber+=1
                self.pods.append(pod.metadata.name)
                self.IPs.append(pod.status.pod_ip)
                self.uids.append(pod.metadata.uid)
        pod_uids[self.msName]=self.uids

    # === Horizontal scaling API ===
    def horizontal_actions(self,nums):
        scale.spec = client.V1ScaleSpec(replicas=nums)
        try:
            apps_v1_api.patch_namespaced_deployment_scale(name=self.msName, namespace=namespace, body=scale)
            print(f"Deployment {self.msName} scaled to {nums} replicas.")
        except client.exceptions.ApiException as e:
            print(f"Exception when scaling Deployment: {e}")
        wait_for_pods_running()
        self.get_my_pods_ips()

    # === Vertical scaling API === baselines都是均匀分配总vertical资源
    def vertical_actions(self,tot_resources,mark="type:NORMAL"):
        # time.sleep(0.5)
        self.get_my_pods_ips()
        node_name=MS_node_mapping[self.msName][0].replace("\n","")
        rpc_set_cpu(node_name,self.uids,tot_resources)
        ts=time.time()
        this_vertical_res=list()#为了将最终纵向资源结果记录进入文件(横向副本数量应该不用记录,最后跑完看一下即可)
        for this_uid in self.uids:
            this_ip=self.IPs[self.uids.index(this_uid)]
            this_vertical_res.append([self.msName,this_uid,this_ip,tot_resources/len(self.uids),mark,ts])#记录分配时间,便于最后算过程中core*hour
            print("Adjusting",self.msName,this_uid,this_ip,"to",tot_resources/len(self.uids),"done.")
        with open("results/Vertical-RES.csv", 'a', newline='') as file:
            writer = csv.writer(file)
            for row in this_vertical_res:
                writer.writerow(row)

    def print_sharedMS(self):
        print("This_shared:",self.msName,self.replicaNumber)
        for i in range(len(self.pods)):
            print(self.pods[i],self.IPs[i],self.uids[i])

def init_MSs():
    global SVC_Shared, MS_node_mapping
    print("===================INIT SHARED MSs====================")
    shared_MSs=["cartservice", "currencyservice", "productcatalogservice", "recommendationservice", "shippingservice"]
    for i in range(len(shared_MSs)):
        sm=SharedMS(shared_MSs[i])
        sm.get_my_pods_ips()
        SVC_Shared.append(sm)
    with open("data/MS_nodes_mapping.json", 'r') as file:
        MS_node_mapping=json.load(file)
    return SVC_Shared

#初始化所有微服务的: 分组\横向副本数\纵向副本数
#相关配置人工手写在
def initialize_MSs_states():
    global SVC_Shared
    print("===================INIT SHARED MSs RES====================")
    with open("data/initialScaling.json", 'r') as file:
        configs= json.load(file)
    #初始化"horizontal"+groups+"vertical"
    for sm in SVC_Shared:
        replicas_num=configs[sm.msName]['replicas']
        tot_resources=configs[sm.msName]['totRES']
        sm.horizontal_actions(replicas_num)
        time.sleep(1)
        sm.vertical_actions(tot_resources,"type:INIT")

def print_all_sharedMSs(mark):
    print("==================== This "+mark+" results: ====================")
    for ms in SVC_Shared:
        ms.print_sharedMS()
        print()

# if __name__ == "__main__":
    