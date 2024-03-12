package hipstershop;

import com.orbitz.consul.AgentClient;
import com.orbitz.consul.Consul;
import com.orbitz.consul.model.agent.ImmutableRegistration;
import com.orbitz.consul.model.agent.Registration;
import java.net.InetAddress;
import java.net.UnknownHostException;

public class ConsulClient {

    private final AgentClient agentClient;

    public ConsulClient(String host, int port) {
        String url = "http://" + host + ":" + String.valueOf(port);
        this.agentClient = Consul.builder().withUrl(url).build().agentClient();
    }

    public void registerService(String name, String id, int port, String ip) throws UnknownHostException {
        if (ip == null || ip.isEmpty()) {
            ip = getLocalIp();
        }

        Registration registration = ImmutableRegistration.builder()
                .id(id)
                .name(name)
                .port(port)
                .address(ip)
                .build();

        System.out.println("Trying to register service [ name: " + name + ", id: " + id + ", address: " + ip + ":" + port + " ]");
        agentClient.register(registration);
    }

    public void deregisterService(String id) {
        agentClient.deregister(id);
    }

    private String getLocalIp() throws UnknownHostException {
        InetAddress localhost = InetAddress.getLocalHost();
        return localhost.getHostAddress();
    }

    public static void main(String[] args) throws UnknownHostException {
        ConsulClient client = new ConsulClient("localhost", 8500);
        client.registerService("service-name", "service-id", 8080, "");
        client.deregisterService("service-id");
    }
}
