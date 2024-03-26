import json
from multiprocessing import Process,Manager
from ERMSBase import SVC_Shared

def Scaling_Decisions():
    return_dict=Horizontal()#先做横向,其中包含了在横向具体action之前的借用资源纵向
    Vertical(return_dict)#启动完所有副本后做纵向,所有的都调整到正好

def run_func(i,this_new_num):
    SVC_Shared[i].horizontal_actions(this_new_num)

def Horizontal():
    return_dict=dict()
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
        return_dict[sm.msName]=tot_QPS
        if(sm.msName in ["srv-text","srv-media"]):
            print("Actual and Monitor QPSs",tot_QPS,data["Recommend-Tot-QPS"])
            tot_QPS=data["Recommend-Tot-QPS"]
        replica_nums=max(int(tot_QPS/min_load)+1,3)
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
    return return_dict
        
def Vertical(return_dict):
    with open("data/scaling_configs.json", 'r') as file:
        data = json.load(file)
    for sm in SVC_Shared:
        print("==============================Vertical "+sm.msName+" ==============================")
        tot_resources=data[sm.msName+"-VerticalAll"]
        if(sm.msName in ["srv-text","srv-media"]):
            print("Actual and Allocate RES",tot_resources,(data["Recommend-Tot-QPS"]/return_dict[sm.msName])*tot_resources*data[sm.msName+"-enlarge"])
            tot_resources=(data["Recommend-Tot-QPS"]/return_dict[sm.msName])*tot_resources*data[sm.msName+"-enlarge"]
        # elif(sm.msName=="profile"):
        #     print("Actual and Allocate RES",tot_resources,tot_resources*data[sm.msName+"-enlarge"])
        #     tot_resources=tot_resources*data[sm.msName+"-enlarge"]
        sm.vertical_actions(tot_resources,"type:NORMAL")
        