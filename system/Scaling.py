#横纵向拓展
import json
import time
from multiprocessing import Process,Manager
from Base import SVC_Shared, init_MSs, print_all_sharedMSs

def Scaling_Decisions():
    Horizontal()#先做横向,其中包含了在横向具体action之前的借用资源纵向
    Vertical()#启动完所有副本后做纵向,所有的都调整到正好

def borrow_vertical(new_groups_number,sm):
    print("###############Processing borrow vertical "+sm.msName+" ###############")
    with open("data/scaling_configs.json", 'r') as file:
        data = json.load(file)
    prev_groups_tmp=sm.now_groups
    prev_groups_IPs=list()
    prev_groups_number=list()
    for k,v in prev_groups_tmp.items():
        prev_groups_number.append(len(v['addresses']))
        prev_groups_IPs.append(v['addresses'])
    print(prev_groups_IPs,prev_groups_number)
    sub_number=list()
    mark=False#标记是否有需要借用的SVC,如果没有就范慧慧
    for i in range(len(new_groups_number)):
        sub_this=new_groups_number[i]-prev_groups_number[i]
        sub_number.append(sub_this)
        if(sub_this>0):
            mark=True
    if(not mark):
        print("NO_BORROW_RETURN")
        return
    print("SUB_NUMBER=",sub_number)
    for i in range(len(sub_number)):
        if(sub_number[i]>0):#说明要增长副本,不做任何操作
            continue
        else:#说明副本数量没变甚至减少,最后一个副本会被借用,其他也有可能(已分配满资源因此不管),只扩大最后,目前简单按照当前group最大量扩大
            this_ip=prev_groups_IPs[i][-1].split(":")[0]#找到最后一个副本对应的IP
            #确定要扩展到的资源量
            this_config=data[sm.msName][list(data[sm.msName].keys())[i]]
            res=0
            if('max_load' in this_config.keys()):#对于无动态图的直接取最大
                res=this_config['max_load']*this_config['slope']+this_config['intercept']
                ######!!!!!!Orcalce vertical resources!!!!!!######
                res=this_config['SingleReplicaMax']
                ######!!!!!!Orcalce vertical resources!!!!!!######
            else:#对于有很多个动态图的,取所有动态图中最大的
                for cg in this_config.keys():
                    res_this=this_config[cg]['max_load']*this_config[cg]['slope']+this_config[cg]['intercept']
                    ######!!!!!!Orcalce vertical resources!!!!!!######
                    res_this=this_config[cg]['SingleReplicaMax']
                    ######!!!!!!Orcalce vertical resources!!!!!!######
                    if(res_this>res):
                        res=res_this
            print(this_ip,this_config,res)
            ##########对于ms中指定的this_ip的pod拓展到res##########
            sm.vertical_update_2(this_ip,res)
            

#水平扩容决策,根据最大并发度
def Horizontal():   
    with open("data/scaling_configs.json", 'r') as file:
        data = json.load(file)
    SVC_Shared_new_groups=list()
    # SVC_Shared horizontal decisions
    for sm in SVC_Shared:
        print("==============================Horizontal "+sm.msName+" ==============================")
        sm.get_upstream_pods_ips()
        real_QPS, wait_QPS=sm.get_QPS()
        configs=data[sm.msName]
        new_groups=list()
        for svc_group in configs.keys():
            max_load=configs[svc_group]["max_load"]
            this_replica=real_QPS[svc_group]/max_load
            replicas=int(this_replica)+1#真实监控的load/单副本最大load+1
            print(sm.msName,svc_group,max_load,real_QPS[svc_group],this_replica)
            new_groups.append(replicas)
        print("new_groups=",new_groups)
        ###算出来新的new_groups就借用
        borrow_vertical(new_groups,sm)
        SVC_Shared_new_groups.append(new_groups)
        # sm.horizontal_udpate_groups(new_groups)
        # sm.get_my_pods_ips()

    #===并行执行横向拓展===
    print("==============================Parallel to executing Horizontal Scahling==============================")
    process_list=[]
    for i in range(len(SVC_Shared)):
        this_new_groups=SVC_Shared_new_groups[i]
        # SVC_Shared[i].horizontal_udpate_groups(this_new_groups)
        p=Process(target=run_func,args=("SVC",i,this_new_groups))
        process_list.append(p)

    for p in process_list:
        p.start()
    for p in process_list:
        p.join()

def run_func(mark,i,this_new_groups):
    if(mark=="SVC"):
        SVC_Shared[i].horizontal_udpate_groups(this_new_groups)


#垂直扩容决策
#需要: (1) 决策到每个replica的资源; (2) 考虑借用资源时多分配, 先暂时不考虑回缩
def Vertical():
    with open("data/scaling_configs.json", 'r') as file:
        data = json.load(file)
    # SVC_Shared vertical decisions
    for sm in SVC_Shared:
        # time.sleep(1)
        print("==============================Vertical "+sm.msName+" ==============================")
        sm.get_upstream_pods_ips()
        real_QPS, wait_QPS=sm.get_QPS()
        configs=data[sm.msName]
        counter=1#标记是第几个group
        for svc_group in configs.keys():
            max_load=configs[svc_group]["max_load"]
            slope,intercept= configs[svc_group]["slope"],configs[svc_group]["intercept"]
            tot_resources=real_QPS[svc_group]*slope+intercept
            ######!!!!!!Orcalce vertical resources!!!!!!######
            Accuracy_rate=real_QPS[svc_group]/configs[svc_group]["OracleQPS"]
            tot_resources=Accuracy_rate*configs[svc_group]["OracleVertical"]
            print("RealQPS, OracleQPS, Montoring_Accuracy, Oracle_Vertical",real_QPS[svc_group],configs[svc_group]["OracleQPS"],Accuracy_rate,configs[svc_group]["OracleVertical"])
            ######!!!!!!Orcalce vertical resources!!!!!!######
            tot=tot_resources
            resources_list=list()#决策分给每个pod的资源量
            full_replica_number=int(real_QPS[svc_group]/max_load)#需要分配满资源的副本数量
            last_pod_load=real_QPS[svc_group]%max_load#最后一个副本需要承担的负载量
            last_replica_number=last_pod_load/max_load#换算为副本数量
            resource_one=tot_resources/(full_replica_number+last_replica_number)#一个副本的资源量
            while(tot_resources>resource_one):
                resources_list.append(resource_one)
                tot_resources-=resource_one
            resources_list.append(tot_resources)  

            # dis-borrow
            # resources_list=list()#决策分给每个pod的资源量
            # full_replica_number=int(real_QPS[svc_group]/max_load)#需要分配满资源的副本数量
            # for i in range(full_replica_number+1):
            #     resources_list.append(tot_resources/(full_replica_number+1))
            print(sm.msName,svc_group,slope,intercept,real_QPS[svc_group],tot,resources_list)
            #####Here to conduct vertical actions##### 根据resource_list进行顺序分配
            sm.vertical_update_1(counter,resources_list)
            counter+=1

#只为了测试,没有用到..
def init_test():
    init_MSs()
    #reservation
    SVC_Shared[0].ready_dict={'reservation': 421206, 'search': 421693}
    SVC_Shared[0].waiting_dict={'reservation': 0, 'search': 0}
    SVC_Shared[0].real_QPS={'reservation': 248.41314096118674, 'search': 257.2024327270388}
    SVC_Shared[0].wait_QPS={'reservation': 0.0, 'search': 0.0}
    SVC_Shared[0].now_groups={'group1': {'addresses': ['10.244.82.180:8087'], 'weight': None}, 'group2': {'addresses': ['10.244.82.181:8087'], 'weight': None}}
    #user
    SVC_Shared[1].ready_dict={'reservation': 421209, 'user': 422948}
    SVC_Shared[1].waiting_dict={'reservation': 0, 'user': 1}
    SVC_Shared[1].real_QPS={'reservation': 248.28013736676252, 'user': 244.27064446518747}
    SVC_Shared[1].wait_QPS={'reservation': 0.0, 'user': 0.15421126544519412}
    SVC_Shared[1].now_groups={'group1': {'addresses': ['10.244.82.182:8086'], 'weight': None}, 'group2': {'addresses': ['10.244.82.183:8086'], 'weight': None}}

    # print_all_sharedMSs("Testing")


if __name__ == "__main__":
    init_test()

    # print(SVC_Shared[0].now_groups)
    # print(CG_Shared[0].now_groups)
    # print(CG_Shared[3].now_groups)

    # borrow_vertical([1,2],SVC_Shared[0])

    Horizontal()
    Vertical()