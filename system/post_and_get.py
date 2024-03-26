import requests
import json


def modify_config(url, modify_group):
    # 将数据编码为 JSON 格式
    json_data = json.dumps(modify_group)

    # 设置请求头
    headers = {
        "Content-Type": "application/json"
    }

    # 发送 POST 请求
    response = requests.post(url, data=json_data, headers=headers)

    # 打印响应结果
    print("[modify_config] response code: ", response.status_code)
    print(response.text)


def get_svc_config(url, svc_name):
    # 设置 GET 请求的参数
    params = {"name": svc_name}

    # 发送带参数的 GET 请求
    response = requests.get(url, params=params)

    # 打印响应结果
    print("[get_svc_config] response code: ", response.status_code)
    return response.json()

def get_counter(url):
    response = requests.get(url)

    # 打印响应结果
    print("[get_counter] response code: ", response.status_code)

    json_data = response.json()

    print(json_data["waiting_requests"])
    print()
    print(json_data["out_ready_requests"])


def load(ip, pro, view, add, checkout):
    if pro:
        product = f"http://{ip}:8080/product"
        data = {'id': '1YMWWN1N4O'}
        response = requests.get(product, params=data)
        # print(product)
        # 检查响应状态码
        if response.status_code == 200:
            print('GET 请求成功')
            # print(response.text)
        else:
            print('GET 请求失败，状态码:', response.status_code)

    if view:
        view = f"http://{ip}:8080/cart/view"
        response = requests.get(view)
        # print(view)
        # 检查响应状态码
        if response.status_code == 200:
            print('GET 请求成功')
            # print(response.text)
        else:
            print('GET 请求失败，状态码:', response.status_code)

    if add:
        add = f'http://{ip}:8080/cart/add'
        data = {'product_id': '0PUK6V6EV0', 'quantity': '3'}
        # 发送 POST 请求
        response = requests.post(add, data=data)
        # 检查响应状态码
        if response.status_code == 200:
            print('POST 请求成功')
        else:
            print('POST 请求失败，状态码:', response.status_code)

    if checkout:
        checkout = f'http://{ip}:8080/cart/checkout'
        data = {
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
        # 发送 POST 请求
        response = requests.post(checkout, data=data)
        
        # 检查响应状态码
        if response.status_code == 200:
            print('POST 请求成功')
        else:
            print('POST 请求失败，状态码:', response.status_code)

if __name__ == "__main__":
    # 目标 URL
    # urlm = "http://localhost:10001/modify-group"
    #
    # # 准备要发送的数据
    # modify_group_number = {
    #     "helloServer": [2, 2, 3]
    # }
    #
    # modify_config(urlm, modify_group_number)
    import os
    import time
    nginxIP=os.popen("kubectl get pods -o wide | grep frontend | awk '{print $6}'").readlines()
    # nginxIP=os.popen("kubectl get svc | grep frontend | awk '{print $3}'").readlines()
    ip = nginxIP[0].replace("\n","")

    for i in range (100):
        load(ip, 1, 1, 1, 1)
        time.sleep(0.1)
        print()

    url_c = f"http://{ip}:10001/counter"
    get_counter(url_c)


    nginxIP=os.popen("kubectl get pods -o wide | grep checkout | awk '{print $6}'").readlines()
    ip = nginxIP[0].replace("\n","")

    url_c = f"http://{ip}:10001/counter"
    get_counter(url_c)