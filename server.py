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
    
    # Send server info
    connectedclients = len(server_info["clients"])
    client.publish("home/wireguard/connectedclients", str(connectedclients))
    client.publish("home/wireguard/interface", server_info.get("interface", "unknown"))
    client.publish("home/wireguard/public_key", server_info.get("public_key", "unknown"))
    client.publish("home/wireguard//listening_port", str(server_info.get("listening_port", "unknown")))

    client.disconnect()

# Get status from Wireguard server by sending gw show command
def GetWGStatus():
    try:
        result = subprocess.run(['wg', 'show'], capture_output=True, text=True, check=True)
        output = result.stdout
        return output
    except subprocess.CalledProcessError as e:
         return {"error": "Error: " + str(e)}
    except FileNotFoundError as e:
        return {"error": "Wireguard not found. Are you sure it is installed?"}


class ClientStatus:
    def __init__(self, peer):
        self.peer = peer
        self.latest_handshake = None
        self.endpoint = ""
        self.allowed_ips = ""
        self.latest_handshake = ""
        self.transfer = ""

    def update_from_line(self, status):
        for line in status.splitlines():
            if line.startswith("  endpoint:"):
                self.endpoint = line.split(": ", 1)[1]
            elif line.startswith("  allowed ips:"):
                self.allowed_ips = line.split(": ", 1)[1]
            elif line.startswith("  latest handshake"):
                latest_handshake = line.split(": ", 1)[1]
                #if latest_handshake != "None":
                    #self.latest_handshake = datetime.strptime(latest_handshake, "%Y-%m-%d %H:%M:%S")
            elif line.startswith("  transfer"):
                self.transfer = line.split(": ", 1)[1]

    def is_active(self):
        if self.latest_handshake:
            #Todo check time since last handshake and compare with connectiontimeout
            #time_since_handshake = (datetime.now() - self.latest_handshake).total_seconds()
            #if(time_since_handshake > connectiontimeout):
            #    return False
            #else:
            #   return True
            return True
        return True

            

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
                current_client = ClientStatus(peer=line.split()[1])
            elif current_client:
                current_client.update_from_line(line)
                

        if current_client:
            self.clients.append(current_client) 

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
            "endpoint": client.endpoint
        }

while True:
    server = ServerStatus()
    server.parse_status(GetWGStatus())
    #wireguard_status = GetWGStatus()
    print("Sendt status...")
    #print(wireguard_status)
    SendToMQTT(os.getenv('mqtt_topic'), server)
    time.sleep(resendrate)

