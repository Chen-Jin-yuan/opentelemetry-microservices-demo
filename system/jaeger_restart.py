import os

def restart_jaeger():
    os.system("kubectl delete -f /state/partition/jcshi/CJY/opentelemetry-microservices-demo/kubernetes-manifests/first-deployment/jaeger.yaml ")
    os.system("kubectl apply -f /state/partition/jcshi/CJY/opentelemetry-microservices-demo/kubernetes-manifests/first-deployment/jaeger.yaml ")


if __name__ == "__main__":
    restart_jaeger()