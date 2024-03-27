import os
import time

def restart():
    os.system("kubectl delete -f /state/partition/jcshi/CJY/opentelemetry-microservices-demo/kubernetes-manifests/after-deployment/")
    os.system("kubectl delete -f /state/partition/jcshi/CJY/opentelemetry-microservices-demo/kubernetes-manifests/first-deployment/")
    time.sleep(12)
    os.system("kubectl apply -f /state/partition/jcshi/CJY/opentelemetry-microservices-demo/kubernetes-manifests/first-deployment/")
    time.sleep(10)
    os.system("kubectl apply -f /state/partition/jcshi/CJY/opentelemetry-microservices-demo/kubernetes-manifests/after-deployment/")

def restart_up():
    os.system("kubectl delete -f /state/partition/jcshi/CJY/opentelemetry-microservices-demo/kubernetes-manifests/after-deployment/frontend-deployment.yaml ")
    os.system("kubectl apply -f /state/partition/jcshi/CJY/opentelemetry-microservices-demo/kubernetes-manifests/after-deployment/frontend-deployment.yaml ")
    os.system("kubectl delete -f /state/partition/jcshi/CJY/opentelemetry-microservices-demo/kubernetes-manifests/after-deployment/checkoutservice-deployment.yaml  ")
    os.system("kubectl apply -f /state/partition/jcshi/CJY/opentelemetry-microservices-demo/kubernetes-manifests/after-deployment/checkoutservice-deployment.yaml  ")


if __name__ == "__main__":
    restart()