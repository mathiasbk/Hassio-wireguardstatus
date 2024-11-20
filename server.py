import os
import subprocess
import paho.mqtt.client as mqtt
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()


## Config
resendrate = 5 
connectiontimeout = 3600 #in seconds

##Home assistant config
mqtt_broker = os.getenv('mqtt_broker', 'localhost')
mqtt_port = int(os.getenv('mqtt_port', 1883))
mqtt_username = os.getenv('mqtt_username', 'default_user')
mqtt_password = os.getenv('mqtt_password', 'default_password')
mqtt_topic_prefix = os.getenv('mqtt_topic', 'home/wireguard')

# Send status to MQTT
def SendToMQTT(topic, message):

    client = mqtt.Client()
    server_info = message.to_dict()
    print("server info ", server_info)
    client.username_pw_set(mqtt_username, mqtt_password)

    try:
            client.connect(mqtt_broker, int(mqtt_port))
    except Exception as e:
        print(f"Error: Could not connect to MQTT broker {mqtt_broker}:{mqtt_port}. Errormessage: {e}")
        return      

    #Check if we got an error
    if isinstance(message, dict) and "error" in message:
        print("Error getting Wireguard status. Make sure you run as admin and Wireguard is installed. Error: " + message["error"])
        client.disconnect()
        return
    else:
        print("Wireguard status retrieved successfully.")
    
    # Send server info
    print("home/wireguard/public_key"  )
    print("server info ", server_info)
    connectedclients = len(server_info["clients"])
    client.publish("home/wireguard/connectedclients", str(connectedclients))
    client.publish("home/wireguard/interface", server_info.get("interface", "unknown"))
    client.publish("home/wireguard/public_key", server_info.get("public_key", "unknown"))
    client.publish("home/wireguard//listening_port", str(server_info.get("listening_port", "unknown")))

    print("connectedclients: " + str(connectedclients))
    # Send data for each client
    for i, client_info in enumerate(server_info["clients"]):
         #In case we dont have any, we set a defaut vaue
        latest_handshake = client_info.get("latest_handshake", "none")
        transfer = client_info.get("transfer", "none")

        topic_suffix = f"/client_{i + 1}"
        client.publish(f"{mqtt_topic_prefix}{topic_suffix}/peer",   str(["peer"]))

        client.publish(f"{mqtt_topic_prefix}/latest_handshake", latest_handshake)
        client.publish(f"{mqtt_topic_prefix}/transfer", transfer)


    #client.publish(topic, message)
    client.disconnect()

def GetWGStatus():
    try:
        result = subprocess.run(['wg', 'show'], capture_output=True, text=True, check=True)
        output = result.stdout
        return output
        clients = []
        client = {}
        for line in output.splitlines():
            if line.startswith("peer:"):
                print("starts" + line)
                if client: 
                    print("found client")
                    #check time since last handshake
                    if "latest_handshake" in client and client["latest_handshake"] != "none":
                        handshake_time = datetime.strptime(client["latest_handshake"], "%Y-%m-%d %H:%M:%S")
                        if(datetime.now() - handshake_time) > timedelta(seconds=connectiontimeout):
                            clients.append(client)
                        else:
                            print("found outdated client")

                client = {"peer": line.split()[1]}

            elif line.startswith("latest handshake:"):
                latest_handshake = line.split(": ", 1)[1]
                if latest_handshake == "None":
                    client["latest_handshake"] = "None"
                else:
                    client["latest_handshake"] = latest_handshake

            elif line.startswith("transfer:"):
                client["transfer"] = line.split(": ", 1)[1]

        if client:
            print("Client: " + str(client))
            if "latest_handshake" in client and client["latest_handshake"] != "None":
                handshake_time = datetime.strptime(client["latest_handshake"], "%Y-%m-%d %H:%M:%S")
                if (datetime.now() - handshake_time).total_seconds() <= connectiontimeout:
                    clients.append(client)
        
        return {"clients": clients}
    
    except subprocess.CalledProcessError as e:
         return {"error": "Error: " + str(e)}
    except FileNotFoundError as e:
        return {"error": "Wireguard not found. Are you sure it is installed?"}


def GetWGPath():
    path = os.environ.get("PATH")
    paths = path.split(";")
    wgpath = ""

    for p in paths:
        if "WireGuard" in p:
            wgpath = p + "\\wireguard.exe"
            break

    return wgpath

class ClientStatus:
    def __init__(self, peer):
        self.peer = peer
        self.latest_handshake = None
        self.transfer = ""
        self.allowed_ips = ""
        self.keepalive = ""

class ServerStatus:
    def __init__(self):
        self.interface = ""
        self.public_key = ""
        self.listening_port = ""
        self.clients = []
        self.status = False

    def parse_status(self, status):
        current_client = None

        for line in status.splitlines():
            if not line.strip():  # Skip empty lines
                continue

            if line.startswith("interface:"):
                self.interface = line.split(": ", 1)[1]
            elif line.startswith("  public key:"):
                self.public_key = line.split(": ", 1)[1]
            elif line.startswith("  listening port:"):
                self.listening_port = line.split(": ", 1)[1]
            elif line.startswith("peer:"):
                if current_client:
                    self.clients.append(current_client)
                #current_client = ClientStatus(peer=line.split()[1])
            elif current_client:
                current_client.update_from_line(line)

        if current_client:
            self.clients.append(current_client)  # Legg til siste klient

    def get_active_clients(self):
        return [client for client in self.clients if client.is_active()]

    def to_dict(self):
        return {
            "interface": self.interface,
            "public_key": self.public_key,
            "listening_port": self.listening_port,
            "status": self.status,
            "clients": [self._client_to_dict(client) for client in self.clients],
            "active_clients": [self._client_to_dict(client) for client in self.get_active_clients()],
        }

    @staticmethod
    def _client_to_dict(client):
        return {
            "peer": client.peer,
            "latest_handshake": client.latest_handshake,
            "transfer": client.transfer,
            "allowed_ips": client.allowed_ips,
            "keepalive": client.keepalive,
        }

while True:
    server = ServerStatus()
    server.parse_status(GetWGStatus())
    #wireguard_status = GetWGStatus()
    print("Sendt status...")
    #print(wireguard_status)
    SendToMQTT(os.getenv('mqtt_topic'), server)
    time.sleep(resendrate)

