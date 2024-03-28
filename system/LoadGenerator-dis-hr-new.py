import requests, os
import math
import random
import time
import numpy as np
import sys
from threading import Thread
from multiprocessing import Process, Manager
import argparse
import subprocess
import pandas

parser = argparse.ArgumentParser(description='--head,--qps,--node_size')

parser.add_argument('-head', '--head', type=int, default=1)
parser.add_argument('-q', '--qps', type=int, default=100)
parser.add_argument('-n', '--node_size', type=int, default=3)
parser.add_argument('-d', '--duration', type=int, default=30)
parser.add_argument('-p', '--process', type=int, default=20)
parser.add_argument('-t', '--types', type=int, default=1)
parser.add_argument('-host','--host', type=str, default="http://10.107.37.224:5000/")
parser.add_argument('-nodeName', '--nodeName', type=str, default='cpu-02')

cg_rate_list_all = [
    [],
    [0.25, 0.25, 0.25, 0.25], # 1
    [1, 0, 0, 0], # 2
    [0, 1, 0, 0], # 3
    [0, 0, 1, 0], # 4
    [0, 0, 0, 1], # 5
    [1.5,1,0.5,1], # lab1
    ]
cg_rate_list = []

data="http://10.106.229.49:5000/"#根据具体情况修改
node_list=['cpu-02','cpu-09', 'cpu-10']


def browse_product():
    params = {'id': '1YMWWN1N4O'}
    url = data + "product"
    return url, params, "browse_product"

def view_cart():
    url = data + "cart/view"
    return url, None, "view_cart"

def add_to_cart():
    url = data + "cart/add"
    params = {'product_id': '0PUK6V6EV0', 'quantity': '3'}
    return url, params, "add_to_cart"

def checkout():
    url = data + "cart/checkout"
    params = {
            'email': 'someone@example.com',
            'street_address': '1600 Amphitheatre Parkway',
            'zip_code': '94043',
            'city': 'Mountain View',
            'state': 'CA',
            'country': 'United States',
            'credit_card_number': '4432-8015-6152-0454',
            'credit_card_expiration_month': '1',
            'credit_card_expiration_year': '2039',
            'credit_card_cvv': '672'
    }
    return url, params, "checkout"


def generate_gaussian_arraival():
    # np.random.normal(4,0.08,250)#mu,sigma,sampleNo
    dis_list = []
    with open("GD_norm.csv") as f:  # use already generated data before
        for line in f:
            dis_list.append(float(line.replace("\n", "")))
    return dis_list


# post a request
def post_request(url, params, service_type, list_99):
    if service_type == "browse_product":
        response = requests.get(url=url, params=params, headers={'Connection': 'close'}, timeout=(100, 100))
    elif service_type == "view_cart":
        response = requests.get(url=url, headers={'Connection': 'close'}, timeout=(100, 100))
    elif service_type == "add_to_cart":
        response = requests.post(url=url, data=params, headers={'Connection': 'close'}, timeout=(100, 100))
    else:
        response = requests.post(url=url, data=params, headers={'Connection': 'close'}, timeout=(100, 100))

    list_99.append([time.time(), response.elapsed.total_seconds() * 1000])


# generate requests with dynamic graphs
def dynamic_graph_rate(dr0, dr1, dr2, dr3):
    # ratio for 4 kinds of svc
    cnt = dr0 + dr1 + dr2 + dr3
    search_ratio = float(dr0) / cnt
    recommend_ratio = float(dr1) / cnt
    user_ratio = float(dr2) / cnt
    reserve_ratio = float(dr3) / cnt
    # for each request, random call graph
    # print(search_ratio,recommend_ratio,reserve_ratio)
    coin = random.random()
    if (coin < search_ratio):
        url, params, service_type = browse_product()
    elif (coin < search_ratio + recommend_ratio):
        url, params, service_type = view_cart()
    elif (coin < search_ratio + recommend_ratio + user_ratio):
        url, params, service_type = add_to_cart()
    else:
        url, params, service_type = checkout()
    return url, params, service_type


def threads_generation(QPS_list, duraion, process_number, list_99_all):  # 250,20
    plist = []
    query_list = []
    dis_list = []
    list_99 = []
    gs_inter = generate_gaussian_arraival()
    for j in range(0, duraion):
        QOS_this_s = int(QPS_list[j] / process_num)
        for i in range(0, QOS_this_s):
            url, params, service_type = dynamic_graph_rate(cg_rate_list[0], cg_rate_list[1],
                                             cg_rate_list[2], cg_rate_list[3])  # determine dynamic call graph
            p = Thread(target=post_request, args=(url, params, service_type, list_99))
            plist.append(p)
            dis_list.append(gs_inter[i % 250] * 250 / QOS_this_s)
    # print("Total %d thread in %d s"%(len(dis_list),duraion))
    fun_sleep_overhead = 0.000075  # overhead to call sleep()function
    # print("begin")
    # For each process, control the QPS=250query/s, and apply Gaussian distribution
    waste_time = 0
    t1 = time.time()
    for i in range(len(plist)):
        t_s = time.time()  # 10^-3ms, negligible
        plist[i].start()
        t_e = time.time()
        # [thread start time] + [sleep() funtion time] + [sleep time] = dis_list[i]
        sleep_time = dis_list[i] / 1000 - ((t_e - t_s) + fun_sleep_overhead)
        if (sleep_time > 0):
            # can compensate
            if (sleep_time + waste_time >= 0):
                time.sleep(sleep_time + waste_time)
                waste_time = 0
            else:
                waste_time += sleep_time
        else:
            waste_time += sleep_time
    t2 = time.time()
    print("done, time count is %f,should be %d, waste_time %f\n" % (t2 - t1, duraion, waste_time))
    # Control all the requests ends before statistics
    for item in plist:
        item.join()
    list_99_all.append(list_99)
    # print(np.percentile(np.array(list_99),99))


def request_test(QPS_list, duraion=20, process_number=20):
    time1 = time.time()
    assert len(QPS_list) == int(duraion)
    process_list = []
    list_99_all = Manager().list()
    for i in range(process_number):
        p = Process(target=threads_generation, args=(QPS_list, duraion, process_number, list_99_all))
        process_list.append(p)
    # start processes
    for p in process_list:
        p.start()
    # print("All processes start.")
    for p in process_list:
        p.join()
    print("All processes done.Total is %f" % (time.time() - time1))
    latency_this_node = []
    for i in list_99_all:
        latency_this_node.extend(i)
    for i in range(len(latency_this_node)):
        latency_this_node[i][0] -= time1
    latency_this_node = sorted(latency_this_node, key=(lambda x: x[0]), reverse=False)
    df = pandas.DataFrame(latency_this_node, columns=['time', 'latency'])
    df.to_csv(f'hr_{args.nodeName}_latency.csv')


def run_on_node(cmd):
    os.system(cmd)


if __name__ == "__main__":
    args = parser.parse_args()
    if args.head:  # 主节点只负责下发请求,不运行负载生成器
        data = args.host
        o_process_list = []
        # 使用分布式节点来发送请求
        for i in range(args.node_size):
            cmd=" ssh {} 'ulimit -n 100000;cd /state/partition/jcshi/CJY/opentelemetry-microservices-demo/system/;python3 LoadGenerator-dis-hr-new.py --head {} --qps {} --node_size {} -p {} -t {} -nodeName {} -d {} -host {}' "\
                .format(node_list[i], 0, args.qps, args.node_size, args.process, args.types, node_list[i], args.duration, data)
            print(cmd)
            p=Process(target=run_on_node,args=(cmd,))
            o_process_list.append(p)
        for p in o_process_list:
            p.start()
        for p in o_process_list:
            p.join()
    else:  # 从节点执行负载发生器
        data = args.host
        print(args)
        os.system("ulimit -n 100000")
        QPS = int(args.qps / args.node_size)
        duraion = args.duration
        process_num = args.process  # 使用的多进程数量
        cg_rate_list = cg_rate_list_all[args.types]  # 使用的call graph比例组
        QPS_list = []
        for i in range(duraion):
            QPS_list += [QPS]
        print(QPS_list)
        request_test(QPS_list, duraion, process_num)