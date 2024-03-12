# pip install python-consul
import consul
import socket
import os


class ConsulClient:
    def __init__(self, host='localhost', port=8500):
        self.consul = consul.Consul(host=host, port=port)

    def register_service(self, name, id, port, ip=''):
        if not ip:
            ip = self.get_local_ip()

        reg = {
            'name': name,
            'service_id': id,
            'port': port,
            'address': ip
        }

        print(f"Trying to register service [ name: {name}, id: {id}, address: {ip}:{port} ]")
        return self.consul.agent.service.register(**reg)

    def register_service_with_check(self, name, id, port, timeout=5, interval=5, deregister_after=30, ip=''):
        if not ip:
            ip = self.get_local_ip()

        check = {
            'HTTP': f"http://{ip}:{port}/actuator/health",
            'Timeout': f"{timeout}s",
            'Interval': f"{interval}s",
            'DeregisterCriticalServiceAfter': f"{deregister_after}s"
        }

        reg = {
            'name': name,
            'service_id': id,
            'port': port,
            'address': ip,
            'check': check
        }

        print(f"Trying to register service with check [ name: {name}, id: {id}, address: {ip}:{port} ]")
        return self.consul.agent.service.register(**reg)

    def deregister_service(self, id):
        return self.consul.agent.service.deregister(id)

    def get_local_ip(self):
        ip_grpc = ''
        ips = [ipnet[4][0] for ipnet in socket.getaddrinfo(socket.gethostname(), None) if ':' not in ipnet[4][0]]

        if not ips:
            raise ValueError("registry: can not find local ip")
        elif len(ips) > 1:
            ip_grpc = ips[0]

            grpc_net = os.getenv("DSB_GRPC_NETWORK")
            if grpc_net:
                _, _, _, _, (ip_net_grpc, _) = socket.getaddrinfo(grpc_net, None)[0]
                for ip in ips:
                    if ip_net_grpc == ip:
                        ip_grpc = ip
                        print(f"gRPC traffic is routed to the dedicated network {ip_grpc}")
                        break
        else:
            ip_grpc = ips[0]

        return ip_grpc
