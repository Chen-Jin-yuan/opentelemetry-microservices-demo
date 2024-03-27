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
pod_uids=dict()#记录msName和uids的对应关系,为最后拿内存使用提供便利

MS_node_mapping=dict()

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
    
    def __init__(self,msName,upNames=list()):
        self.msName=msName
        self.upNames=upNames#此共享微服务的上游微服务名称(可能有多个upstream)
        self.upPods=list()#此共享微服务的上游微服务所有pod
        self.upIPs=list()#上游微服务的所有IPs
        self.pods=list()
        self.IPs=list()
        self.replicaNumber=0
        self.ready_dict=dict()#当下状态下ready被发送的请求
        self.waiting_dict=dict()#当下状态下已经排队的请求
        self.real_QPS=dict()#真实负载query/second
        self.wait_QPS=dict()#等待队列query/second
        self.timestamp=0#用于监控精准计时
        self.now_groups=dict()#对于本微服务,目前的副本分组配置
        self.uids=list()#用于进行资源分配

    def get_QPS(self):
        return self.real_QPS, self.wait_QPS

    def get_my_pods_ips(self):
        global pod_uids
        self.pods,self.IPs,self.replicaNumber,self.uids=[],[],0,[]
        deployment_name=self.msName
        pods_all = v1.list_namespaced_pod(namespace)
        for pod in pods_all.items:
            if pod.metadata.labels.get('app') == deployment_name:
                self.replicaNumber+=1
                self.pods.append(pod.metadata.name)
                self.IPs.append(pod.status.pod_ip)
                self.uids.append(pod.metadata.uid)
        #这些pods\ips是无序的(没有按照group+ip进行排序)
        pod_uids[self.msName]=self.uids
    
    def get_upstream_pods_ips(self):
        self.upPods,self.upIPs=[],[]
        for ms_name in self.upNames:
            self.upPods.append([])
            self.upIPs.append([])
            deployment_name=ms_name
            pods_all = v1.list_namespaced_pod(namespace)
            for pod in pods_all.items:
                if pod.metadata.labels.get('app') == deployment_name:
                    self.upPods[-1].append(pod.metadata.name)
                    self.upIPs[-1].append(pod.status.pod_ip)

    def return_read_waiting(self):
        return self.real_QPS, self.wait_QPS

    # === Monitoring API ===
    def get_ready_waiting(self):#已经准备好发送的总数和排队总数
        ready_dict_temp=self.ready_dict
        waiting_dict_temp=self.waiting_dict
        self.ready_dict,self.waiting_dict,self.real_QPS,self.wait_QPS={},{},{},{}
        time_prev=self.timestamp
        for i in range(len(self.upNames)):
            for j in range(len(self.upIPs[i])):
                # print(self.upPods[i][j],self.upIPs[i][j])
                print("++++++++++++++++Getting counts from "+self.upNames[i]+self.upIPs[i][j]+" ++++++++++++++++")
                url="http://"+self.upIPs[i][j]+":10001/counter"
                self.timestamp=time.time()
                response=requests.get(url)
                if(response.status_code!=200):
                    print("Get_ready_waiting error, Error Code=",response.status_code)
                    return
                json_data=response.json()
                for k,v in json_data["out_ready_requests"].items():
                    if k.split(":")[0] not in self.IPs:
                        continue
                    # print(k,v['type_counter'])
                    for key in v['type_counter']:
                        if(key not in self.ready_dict.keys()):
                            self.ready_dict[key]=v['type_counter'][key]
                        else:
                            self.ready_dict[key]+=v['type_counter'][key]
                for k,v in json_data["waiting_requests"].items():
                    if k.split(":")[0] not in self.IPs:
                        continue
                    # print(k,v['type_counter'])
                    for key in v['type_counter']:
                        if(key not in self.waiting_dict.keys()):
                            self.waiting_dict[key]=v['type_counter'][key]
                        else:
                            self.waiting_dict[key]+=v['type_counter'][key]
        # print("ready=",self.ready_dict)
        # print("waiting=",self.waiting_dict)
        # print("ready_last=",ready_dict_temp)
        # print("waiting_last=",waiting_dict_temp)
        for key in self.ready_dict.keys():
            if(ready_dict_temp=={}):
                self.real_QPS[key]=(self.ready_dict[key] - 0)/(self.timestamp-time_prev)
            else:
                self.real_QPS[key]=(self.ready_dict[key]-ready_dict_temp[key])/(self.timestamp-time_prev)
            self.wait_QPS[key]=self.waiting_dict[key]
        # print("real_QPS=",self.real_QPS)
        # print("wait_QPS=",self.real_QPS)
        return self.real_QPS, self.wait_QPS

    def get_now_groups(self):
        url_up = "http://"+self.upIPs[0][0]+":10001/svc-info"#上游IP
        print(self.upIPs[0][0],self.msName)
        params = {"name": self.msName}
        response = requests.get(url_up, params=params)
        if(response.status_code!=200):
            print("Get_now_groups error, Error Code=",response.status_code)
            return
        self.now_groups=json.loads(response.text)
        for k,v in self.now_groups.items():
            self.now_groups[k]['addresses'].sort()#排序

    # === Horizontal scaling API ===
    def horizontal_udpate_groups(self,new_groups=[]):#like new_groups=[1, 5] 更新grpc配置, 完成scale
        # 1. 通知grpc框架 (对于所有的上游)
        for i in range(len(self.upNames)):
            for j in range(len(self.upIPs[i])):
                print("++++++++++++++++Notifying group change "+self.upNames[i]+self.upIPs[i][j]+" ++++++++++++++++")
                urlm = "http://"+self.upIPs[i][j]+":10001/modify-group"
                modify_group = {
                    self.msName: new_groups
                }
                json_data = json.dumps(modify_group)
                headers = {
                    "Content-Type": "application/json"
                }
                response = requests.post(urlm, data=json_data, headers=headers)
                if(response.status_code!=200):
                    print("update_groups error, Error Code=",response.status_code)
                    return
        # 2.对于所有减少的group进行定向删除
        index=0
        for k,v in self.now_groups.items():
            if(k=="notGrouped"):
                continue
            print("Len-compare:",new_groups[index],len(v['addresses']))
            if(new_groups[index]>len(v['addresses'])):#新的配置大于原有的,不需要定向删除
                index+=1
                continue
            sub=len(v['addresses'])-new_groups[index]#需要定向删除的数量
            del_IPs_list=v['addresses'][0:sub]#删除的pod ips
            for dip in del_IPs_list:
                pod_this=self.pods[self.IPs.index(dip.split(":")[0])]#定位需要删除的pod_name
                try:
                    v1.delete_namespaced_pod(name=pod_this, namespace=namespace)
                    print(f"Pod {pod_this} in namespace {namespace} deleted.")
                except client.exceptions.ApiException as e:
                    print(f"Exception when deleting Pod: {e}")
            index+=1
        # 3.按照数量进行scale
        scale.spec = client.V1ScaleSpec(replicas=sum(new_groups))
        try:
            apps_v1_api.patch_namespaced_deployment_scale(name=self.msName, namespace=namespace, body=scale)
            print(f"Deployment {self.msName} scaled to {sum(new_groups)} replicas.")
        except client.exceptions.ApiException as e:
            print(f"Exception when scaling Deployment: {e}")
        # if(self.replicaNumber<sum(new_groups)):#扩展出更多pod时需要等待
        wait_for_pods_running()
        # 4.更新now_groups等
        self.get_my_pods_ips()
        self.get_upstream_pods_ips()
        # self.get_ready_waiting()
        self.get_now_groups()
        # print(self.now_groups)

    # === Vertical scaling API ===
    #counter标记是第几个group,传入resource列表,对于所有pod进行调整=>用于vertical
    def vertical_update_1(self,counter,resource_list=[],mark="type:NORMAL"):
        self.get_my_pods_ips()
        self.get_now_groups()
        ips=self.now_groups["group"+str(counter)]['addresses']#需要按照now_groups ip顺序来分配
        print("group"+str(counter),ips)
        while(len(ips)!=len(resource_list)):#可能group更新有延迟
            time.sleep(0.1)
            self.get_now_groups()
            ips=self.now_groups["group"+str(counter)]['addresses']#需要按照now_groups ip顺序来分配
        assert len(ips)==len(resource_list)
        this_vertical_res=list()#为了将最终纵向资源结果记录进入文件(横向副本数量应该不用记录,最后跑完看一下即可)
        for i in range(len(resource_list)):
            node_name=MS_node_mapping[self.msName][0].replace("\n","")
            this_ip=ips[i].split(":")[0]
            this_uid=self.uids[self.IPs.index(this_ip)]
            this_res=resource_list[i]
            rpc_set_cpu(node_name,this_uid,this_res)
            ts=time.time()
            this_vertical_res.append([self.msName,this_uid,this_ip,this_res,mark,ts])#记录分配时间,便于最后算过程中core*hour
            print("Adjusting",self.msName,this_uid,this_ip,"to",this_res,"done.")
        with open("results/Vertical-RES.csv", 'a', newline='') as file:
            writer = csv.writer(file)
            for row in this_vertical_res:
                writer.writerow(row)
    #根据传入的ip寻找pod进行调整=>用于borrowing
    def vertical_update_2(self,this_ip="",res=0):
        # print(self.IPs)
        this_uid=self.uids[self.IPs.index(this_ip)]
        node_name=MS_node_mapping[self.msName][0].replace("\n","")
        rpc_set_cpu(node_name,this_uid,res)
        ts=time.time()
        print("Adjusting",self.msName,this_uid,this_ip,"to",res,"done.")
        with open("results/Vertical-RES.csv", 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([self.msName,this_uid,this_ip,res,"type:BORROW",ts])

    def print_sharedMS(self):
        print("This_shared:",self.msName,self.replicaNumber)
        for i in range(len(self.pods)):
            print(self.pods[i],self.IPs[i],self.uids[i])
        print("Upstream MSs:",self.upNames)
        for i in range(len(self.upNames)):
            for j in range(len(self.upPods[i])):
                print(self.upPods[i][j],self.upIPs[i][j])
        print("Ready=",self.ready_dict)
        print("Waiting=",self.waiting_dict)
        print("Real_QPS=",self.real_QPS)
        print("Wait_QPS=",self.wait_QPS)
        print("Now_groups",self.now_groups)



def init_MSs():
    global SVC_Shared, MS_node_mapping
    print("===================INIT SHARED MSs====================")
    shared_MSs=["cartservice", "currencyservice", "productcatalogservice", "recommendationservice", "shippingservice"]#这里有两个上级可能会有问题???
    up_MSs=[["frontend","checkoutservice"],["frontend","checkoutservice"],["frontend","checkoutservice"],
            ["frontend"], ["frontend","checkoutservice"]]
    
    for i in range(len(shared_MSs)):
        sm=SharedMS(shared_MSs[i],up_MSs[i])
        sm.get_my_pods_ips()
        sm.get_upstream_pods_ips()
        sm.get_ready_waiting()
        sm.get_now_groups()
        SVC_Shared.append(sm)

    with open("data/MS_nodes_mapping.json", 'r') as file:
        MS_node_mapping=json.load(file)

    return SVC_Shared

def initialize_MSs_states():
    global SVC_Shared
    print("===================INIT SHARED MSs RES====================")
    with open("initial/initialScaling.json", 'r') as file:
        configs= json.load(file)
    #初始化"horizontal"+groups+"vertical"
    for sm in SVC_Shared:
        this_group=configs[sm.msName]['grouped']
        this_res=configs[sm.msName]['vertical']
        sm.horizontal_udpate_groups(this_group)
        for i in range(len(this_res)):
            counter=i+1
            sm.vertical_update_1(counter,this_res[i],"type:INIT")
    

def print_all_sharedMSs(mark):
    print("==================== This "+mark+" results: ====================")
    for ms in SVC_Shared:
        ms.print_sharedMS()
        print()

if __name__ == "__main__":
    
    with open("data/MS_nodes_mapping.json", 'r') as file:
        MS_node_mapping=json.load(file)
    
    sm_user=SharedMS("user",["frontend"])
    sm_user.get_my_pods_ips()
    sm_user.get_upstream_pods_ips()
    sm_user.get_ready_waiting()
    sm_user.get_now_groups()
    sm_user.print_sharedMS()
    t1=time.time()
    sm_user.horizontal_udpate_groups([2,2])#1,1->5,5 14.8秒 #5,5->1,1 2.74秒
    t2=time.time()
    print(t2-t1)
    sm_user.print_sharedMS()
    sm_user.vertical_update_1(2,[30,40])
    sm_user.vertical_update_2("10.244.82.183",80)


    

    # time.sleep(5)
    # sm_user.get_ready_waiting()#overhead=13ms
    # sm_user.print_sharedMS()

    # init_MSs()
    '''
    sm_score=CallGraphSharedMS("score",["recommendation"])
    sm_score.get_my_pods_ips()
    sm_score.get_upstream_pods_ips()
    sm_score.get_ready_waiting()
    with open("data/Recommend_CallGraphs_base.json", 'r') as file:
        data = json.load(file)
    sm_score.cal_detailed_QPS(data)
    sm_score.get_now_groups()
    input_configs={"GetScoreNew":["CG2"],"GetScoreNew2":["CG4","CG6","CG7"]}
    sm_score.set_functions_CG_mapping(input_configs)
    sm_score.print_sharedMS()
    # t1=time.time()
    # sm_price.horizontal_udpate_groups([1,1])#1,1->5,5 14.8秒 #5,5->1,1 2.74秒
    # t2=time.time()
    # print(t2-t1)
    # sm_price.print_sharedMS()
    time.sleep(5)
    sm_score.get_ready_waiting()#overhead=13ms
    with open("data/Recommend_CallGraphs_base.json", 'r') as file:
        data = json.load(file)
    sm_score.cal_detailed_QPS(data)
    sm_score.print_sharedMS()
    '''
    '''
    sm_profile=SharedMS("profile",["frontend"])
    sm_profile.get_my_pods_ips()
    sm_profile.get_upstream_pods_ips()
    sm_profile.get_ready_waiting()
    sm_profile.get_now_groups()
    sm_profile.print_sharedMS()
    # t1=time.time()
    # sm_profile.horizontal_udpate_groups([5,3])#1,1->5,5 14.8秒 #5,5->1,1 2.74秒
    # t2=time.time()
    # print(t2-t1)
    # sm_profile.print_sharedMS()
    time.sleep(5)
    sm_profile.get_ready_waiting()#overhead=13ms
    sm_profile.print_sharedMS()
    '''
    '''
    sm_reservation=SharedMS("reservation",["frontend"])
    sm_reservation.get_my_pods_ips()
    sm_reservation.get_upstream_pods_ips()
    sm_reservation.get_ready_waiting()
    sm_reservation.get_now_groups()
    sm_reservation.print_sharedMS()
    # t1=time.time()
    # sm_reservation.horizontal_udpate_groups([1,1])#1,1->5,5 14.8秒 #5,5->1,1 2.74秒
    # t2=time.time()
    # print(t2-t1)
    # sm_reservation.print_sharedMS()
    time.sleep(5)
    sm_reservation.get_ready_waiting()#overhead=13ms
    sm_reservation.print_sharedMS()
    '''
   
    '''
    sm_dis=SharedMS("dis",["recommendation"])
    sm_dis.get_my_pods_ips()
    sm_dis.get_upstream_pods_ips()
    sm_dis.get_ready_waiting()
    sm_dis.get_now_groups()
    sm_dis.print_sharedMS()
    # t1=time.time()
    # sm_dis.horizontal_udpate_groups([1,1])#1,1->5,5 14.8秒 #5,5->1,1 2.74秒
    # t2=time.time()
    # print(t2-t1)
    # sm_dis.print_sharedMS()
    time.sleep(5)
    sm_dis.get_ready_waiting()#overhead=13ms
    sm_dis.print_sharedMS()
    '''
    '''
    sm_score=SharedMS("score",["recommendation"])
    sm_score.get_my_pods_ips()
    sm_score.get_upstream_pods_ips()
    sm_score.get_ready_waiting()
    sm_score.get_now_groups()
    sm_score.print_sharedMS()
    t1=time.time()
    sm_score.horizontal_udpate_groups([1,1])#1,1->5,5 14.8秒 #5,5->1,1 2.74秒
    t2=time.time()
    print(t2-t1)
    sm_score.print_sharedMS()
    # time.sleep(5)
    # sm_score.get_ready_waiting()#overhead=13ms
    # sm_score.print_sharedMS()
    '''
    '''
    sm_price=SharedMS("score",["recommendation"])
    sm_price.get_my_pods_ips()
    sm_price.get_upstream_pods_ips()
    sm_price.get_ready_waiting()
    sm_price.get_now_groups()
    sm_price.print_sharedMS()
    # t1=time.time()
    # sm_price.horizontal_udpate_groups([1,1])#1,1->5,5 14.8秒 #5,5->1,1 2.74秒
    # t2=time.time()
    # print(t2-t1)
    # sm_price.print_sharedMS()
    time.sleep(5)
    sm_price.get_ready_waiting()#overhead=13ms
    sm_price.print_sharedMS()
    '''
