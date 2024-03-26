import os
import pandas as pd
import csv
from kubernetes import client, config

config.kube_config.load_kube_config()

#分配各个容器的优先级,跑了之后发现没有调入口共享微服务frontend
def apply_priority(namespace, data_path,data,frontend_configs,svc_priority,mark):    
    priority = pd.DataFrame(data)
    print(priority)
    print()
    parent_data, target_data = merge_k8s_data_to_priority(namespace, priority)
    print(target_data)
    print(parent_data)
    print()
    rules, virtual_if_count = generate_if_data(priority, parent_data, target_data)
    print(virtual_if_count)
    ip_priority_0=frontend_configs[svc_priority[0]]
    ip_priority_1=frontend_configs[svc_priority[1]]
    print(ip_priority_0,ip_priority_1)
    rules = rules[rules['src_ip'].isin(list(frontend_configs.values()))]
    rules = rules[rules['priority'] == 0].reset_index(drop=True)
    rules.loc[rules['src_ip'] == ip_priority_0, 'priority'] = 0
    rules.loc[rules['src_ip'] == ip_priority_1, 'priority'] = 1
    print(rules)
    print()
    generate_scripts(virtual_if_count, rules, data_path,mark)
    deploy_vifs(data_path)

#对于共享微服务，收集Kubernetes集群中运行的微服务数据，并将这些数据与优先级信息合并
#最后获得tareget和parent的name\pod_ip\host_ip\container_ip\cpu\mem
def merge_k8s_data_to_priority(namespace, priority: pd.DataFrame):
    data_columns = ["microservice", "pod_ip", "host_ip", "container_id", "cpu", "mem"]
    target_data = pd.DataFrame(columns=data_columns)#目标微服务相关数据
    parent_data = pd.DataFrame(columns=data_columns)#父微服务相关数据
    target_ms_set = set(priority["microservice"].unique().tolist())#从priority中提取目标微服务集合
    parent_ms_set = set(priority["parent"].unique().tolist())#从priority中提取父微服务集合
    # print(target_ms_set)#目标共享微服务集合
    # print(parent_ms_set)#目标共享微服务的父微服务集合
    # print()
    #以下是为了获取namespace内所有微服务相关信息
    v1 = client.CoreV1Api()
    res = v1.list_namespaced_pod(namespace=namespace, watch=False)
    for i in res.items:
        pod_name = "-".join(str(i.metadata.name).split("-")[:-2])
        pod_ip = i.status.pod_ip
        host_ip = i.status.host_ip
        try:
            container_id = i.status.container_statuses[0].container_id.split("//")[1][
                0:12
            ]
        except:
            container_id = ""
        try:
            cpu = i.spec.containers[0].resources.limits["cpu"]
            memory = i.spec.containers[0].resources.limits["memory"]
        except:
            cpu = 32
            memory = 64
        data = pd.DataFrame(
            [
                {
                    "microservice": pod_name,
                    "host_ip": host_ip,
                    "pod_ip": pod_ip,
                    "container_id": container_id,
                    "cpu": cpu,
                    "mem": memory,
                }
            ]
        )
        if pod_name in target_ms_set:
            target_data = pd.concat([target_data, data])
        if pod_name in parent_ms_set:
            parent_data = pd.concat([parent_data, data])
    return parent_data, target_data

#基于合并后的数据生成虚拟接口(VIFs,virtual network interfaces)的规则和计数
def generate_if_data(
    priority: pd.DataFrame, parent_data: pd.DataFrame, target_data: pd.DataFrame
):
    left = (
        target_data.merge(priority, on="microservice")
        .rename(
            columns={
                "pod_ip": "dest_ip",
                "microservice": "dest_ms",
                "container_id": "dest_container",
                "host_ip": "dest_host",
            }
        )
        .drop(columns=["cpu", "mem", "service"])
    )
    # print(left)
    # print()
    right = parent_data[["microservice", "pod_ip"]].rename(
        columns={"microservice": "parent", "pod_ip": "src_ip"}
    )
    # print(right)
    # print()
    rules = left.merge(right, on="parent")[
        ["dest_host", "dest_container", "src_ip", "priority"]
    ]
    # print(rules)
    # print()
    virtual_if_count: pd.DataFrame = (
        rules.groupby("dest_host")
        .apply(lambda x: len(x.groupby("dest_container")))
        .to_frame()
        .reset_index()
        .rename(columns={0: "count", "dest_host": "host"})
    )
    # print(virtual_if_count)
    # print()
    #rules: 定义了每个微服务的流量控制规则
    #virtual_if_count: 每个宿主机上的虚拟接口数量
    return rules, virtual_if_count

#生成应用这些流量整形规则在每个节点上的shell脚本(重要的生效规则都在这里)
def generate_scripts(virtual_if_count: pd.DataFrame, rules: pd.DataFrame, data_path, mark):
    global index_base
    result_path = f"{data_path}"
    # os.system(f"rm -rf {result_path}")
    # os.system(f"mkdir -p {result_path}")

    for _, row in virtual_if_count.iterrows():
        host = str(row["host"])
        if_count = int(row["count"])
        print(host)
        print(if_count)
        clear_lines = ""
        # Config number of virtual interface
        lines = f"# Config number of virtual interface\n"
        lines += f"modprobe ifb numifbs={if_count}\n"
        lines += f'echo "Set numifbs to {if_count}"\n'
        host_rules = rules.loc[rules["dest_host"] == host]
        print(host_rules["dest_container"].unique().tolist())
        base=index_base
        for container_index, container_id in enumerate(
            host_rules["dest_container"].unique().tolist()
        ):
            index_base+=1
            container_rules = host_rules.loc[rules["dest_container"] == container_id]
            print(container_index+base)
            ifb = f"ifb{container_index+base}"
            # Get container's network interface
            lines += f"# Get container's network interface\n"
            lines += f'echo "Working on container {container_index+base}"\n'
            lines += f"NET=`docker exec -i {container_id} bash -c 'cat /sys/class/net/eth*/iflink'`\n"
            lines += f"NET=`echo $NET|tr -d '\\r'`\n"
            lines += f"VETH=`grep -l $NET /sys/class/net/cali*/ifindex`\n"#这里有问题是空的,他可能用的不是calico
            lines += f"VETH=`echo $VETH|sed -e 's;^.*net/\(.*\)/ifindex$;\\1;'`\n"#获取对应虚拟网卡
            lines += f"VETH=`echo $VETH|tr -d '\\r'`\n"
            lines += f'echo "Get container\'s network interface OK"\n'
            # Create virtual interface
            lines += f"# Create virtual interface\n"
            lines += f"ip link delete {ifb}\n"
            lines += f"ip link add {ifb} type ifb\n"
            lines += f"ip link set {ifb} up\n"
            lines += f'echo "Create network virtual interface OK"\n'#虚拟网卡创建结束
            # Redirect to virtual interface
            lines += f"# Redirect to virtual interface\n"
            lines += f"tc qdisc del dev $VETH handle ffff: ingress\n"
            lines += f"tc qdisc add dev $VETH handle ffff: ingress\n"
            lines += f"tc filter add dev $VETH parent ffff: \\\n"
            lines += f"    protocol ip u32 match u32 0 0 \\\n"
            lines += f"    flowid 1:1 action mirred egress redirect dev {ifb}\n"
            lines += f'echo "Add redirection OK"\n'
            # Add root
            lines += f"# Add root\n"
            lines += f"tc qdisc add dev {ifb} root handle 1:0 htb default 10\n"
            lines += f'echo "Add root OK"\n'
            # Add classes
            lines += f"# Add classes\n"
            print("xxxxxx")
            print(container_rules)
            for class_index, (_, rule) in enumerate(container_rules.iterrows()):
                src = str(rule["src_ip"]) + "/32"
                priority = int(rule["priority"])
                # with open("record.csv",mode='a',newline='') as file:
                #     writer=csv.writer(file)
                #     writer.writerow([src,str(priority)])
                lines += f"tc class add dev {ifb} parent 1:0 classid 1:{class_index + 1} htb prio {priority} rate 10Mbit\n"
                lines += f"tc filter add dev {ifb} protocol ip parent 1:0 u32 match ip src {src} flowid 1:{class_index + 1}\n"
            lines += f'echo "Add classes OK"\n'

            # Clear
            clear_lines += f"NET=`docker exec -i {container_id} bash -c 'cat /sys/class/net/eth*/iflink'`\n"
            clear_lines += f"NET=`echo $NET|tr -d '\\r'`\n"
            clear_lines += f"VETH=`grep -l $NET /sys/class/net/cali*/ifindex`\n"
            clear_lines += f"VETH=`echo $VETH|sed -e 's;^.*net/\(.*\)/ifindex$;\\1;'`\n"
            clear_lines += f"VETH=`echo $VETH|tr -d '\\r'`\n"
            clear_lines += "tc qdisc del dev $VETH handle ffff: ingress\n"
            clear_lines += f"ip link delete {ifb}\n"
        lines += f'echo "Priority implemented"\n'
        with open(f"{result_path}/{host}-"+mark+"-tc.sh", "w") as f:#配置每一个server上的tc规则脚本
            f.write(lines)
        with open(f"{result_path}/{host}-"+mark+"-clean.sh", "w") as f:#清除每一个server上的tc规则脚本
            f.write(clear_lines)

#部署生成的脚本,remote到每一台server上去执行
def deploy_vifs(data_path):
    scripts_path = f"{data_path}"
    scripts = [x for x in os.listdir(scripts_path) if x[-5:] == "tc.sh"]
    for script in scripts:
        host = script.split("-")[0]
        script_path = f"{scripts_path}/{script}"
        print(script_path)
        remote_execute_script(host, script_path, script)
        os.system("bash "+script_path)


def clear_vifs(data_path):
    scripts_path = f"{data_path}"
    try:
        scripts = [x for x in os.listdir(scripts_path) if x[-8:] == "clean.sh"]
        for script in scripts:
            host = script.split("-")[0]
            script_path = f"{scripts_path}/{script}"
            remote_execute_script(host, script_path, script)
            print(script_path)
            os.system("bash "+script_path)

    except:
        print("No vifs needed to be clean")

#拷贝并ssh到远程主机进行执行
def remote_execute_script(host, script_path, script):
    user = "root"
    if(host=="10.2.64.6"):
        os.system(f"bash ./priorityData/{script}")
    else:
        os.system(f"scp {script_path} {user}@{host}:/tmp")
        os.system(f"ssh {user}@{host} bash /tmp/{script}")
        # os.system(f"ssh {user}@{host} rm /tmp/{script}")

index_base=0

#设定profile\reservation\user三个微服务的优先级
def SetupShared():
    #对应的service\SharedMS\parent\priority关系设定
    #设定profile-microservice
    data = {
        'service': ['Search', 'Recommendation'],
        'microservice': ['profile', 'profile'],
        'parent': ['frontend', 'frontend'],
        'priority': [1, 0]
    } 
    #frontend_ip与svc关系对应设定
    frontend_configs={
        "Search":"10.244.145.130",
        "Recommendation":"10.244.145.137",
    }
    #同样是priority设定
    svc_priority={
        0:"Recommendation",
        1:"Search"
    }
    apply_priority("default","priorityData",data,frontend_configs,svc_priority,"profile")
    #设定reservation-microservice
    data = {
        'service': ['Search', 'Reservation'],
        'microservice': ['reservation', 'reservation'],
        'parent': ['frontend', 'frontend'],
        'priority': [1, 0]
    } 
    #frontend_ip与svc关系对应设定
    frontend_configs={
        "Search":"10.244.145.130",
        "Reservation":"10.244.145.186",
    }
    #同样是priority设定
    svc_priority={
        0:"Reservation",
        1:"Search"
    }
    apply_priority("default","priorityData",data,frontend_configs,svc_priority,"reservation")
    #设定user-microservice
    data = {
        'service': ['User', 'Reservation'],
        'microservice': ['user', 'user'],
        'parent': ['frontend', 'frontend'],
        'priority': [1, 0]
    } 
    #frontend_ip与svc关系对应设定
    frontend_configs={
        "User":"10.244.145.185",
        "Reservation":"10.244.145.186",
    }
    #同样是priority设定
    svc_priority={
        0:"Reservation",
        1:"User"
    }
    apply_priority("default","priorityData",data,frontend_configs,svc_priority,"user")

#用于测试
if __name__ == "__main__":
    SetupShared()
    clear_vifs("priorityData")