import subprocess

path = "/state/partition/jcshi/CJY/opentelemetry-microservices-demo/system/"
# 需要在 root 用户下运行
def scp_file_to_remote(node):
    try:
        # 构建scp命令
        command = f"scp -r {path} {node}:/state/partition/jcshi/CJY/opentelemetry-microservices-demo/"

        # 执行scp命令
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)

        # 检查命令是否成功执行
        if result.returncode == 0:
            print(f"File copied successfully to {node}")
        else:
            print("Error copying file:")
            print(result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

# 需要在非 root 用户下运行
def scp_file_from_remote(node):
    cmd = f"sudo -u jcshi ssh {node} 'cd /state/partition/jcshi/CJY/tool/LoadGenerator;scp hr_{node}_latency.csv jcshi@cpu-06:~/CJY/tool/latency_csv; scp {node}_timeout_count.txt jcshi@cpu-06:~/CJY/tool/latency_csv'"
    result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
    # 检查命令是否成功执行
    if result.returncode == 0:
        print(f"File copied successfully from {node}")
    else:
        print("Error copying file:")
        print(result.stderr)

def scp_to(node_list):
    for node in node_list:
        scp_file_to_remote(node)

def scp_from(node_list):
    for node in node_list:
        scp_file_from_remote(node)
