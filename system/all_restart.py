import os

def restart():
    os.system("kubectl delete -f /state/partition/jcshi/CJY/opentelemetry-microservices-demo/kubernetes-manifests/after-deployment/")
    os.system("kubectl apply -f /state/partition/jcshi/CJY/opentelemetry-microservices-demo/kubernetes-manifests/after-deployment/")


if __name__ == "__main__":
    restart()