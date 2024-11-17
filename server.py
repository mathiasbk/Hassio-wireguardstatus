import os
import subprocess
import paho.mqtt.client as mqtt
import time
from dotenv import load_dotenv

load_dotenv()


## Config
resendrate = 5 

##Home assistant config
mqtt_broker = os.getenv('mqtt_broker', 'localhost')
mqtt_port = int(os.getenv('mqtt_port', 1883))
mqtt_username = os.getenv('mqtt_username', 'default_user')
mqtt_password = os.getenv('mqtt_password', 'default_password')
mqtt_topic_prefix = os.getenv('mqtt_topic', 'home/wireguard/status')

# Send status to MQTT
def SendToMQTT(topic, message):
    client = mqtt.Client()
    client.username_pw_set(mqtt_username, mqtt_password)
    try:
            client.connect(mqtt_broker, int(mqtt_port))
    except Exception as e:
        print(f"Error: Could not connect to MQTT broker {mqtt_broker}:{mqtt_port}. Errormessage: {e}")
        return      

    # Send server info
    server_info = message.get("server_info", {})
    connectedclients = len(message["clients"])

    client.publish(f"{mqtt_topic_prefix}/wireguard/connectedclients", str(connectedclients))
    client.publish(f"{mqtt_topic_prefix}/wireguard/interface", server_info.get("interface", "unknown"))
    client.publish(f"{mqtt_topic_prefix}/wireguard/public_key", server_info.get("public_key", "unknown"))
    client.publish(f"{mqtt_topic_prefix}/wireguard/listening_port", str(server_info.get("listening_port", "unknown")))

    print("connectedclients: " + str(connectedclients))
    # Send data for each client
    for i, client_info in enumerate(message["clients"]):
         #In case we dont have any, we set a defaut vaue
        latest_handshake = client_info.get("latest_handshake", "none")
        transfer = client_info.get("transfer", "none")

        topic_suffix = f"/client_{i + 1}"  # Unik identifikator for hver klient
        client.publish(f"{mqtt_topic_prefix}{topic_suffix}/peer",   str(["peer"]))

        client.publish(f"{mqtt_topic_prefix}/latest_handshake", latest_handshake)
        client.publish(f"{mqtt_topic_prefix}/transfer", transfer)


    #client.publish(topic, message)
    client.disconnect()

def GetWGStatus():
    try:
        result = subprocess.run(['wg', 'show'], capture_output=True, text=True, check=True)
        output = result.stdout

        clients = []
        client = {}
        for line in output.splitlines():
            if line.startswith("peer:"):
                if client:  # Hvis det allerede er en klient, lagre den
                    clients.append(client)
                client = {"peer": line.split()[1]}
            elif line.startswith("latest handshake:"):
                client["latest_handshake"] = line.split(": ", 1)[1]
            elif line.startswith("transfer:"):
                client["transfer"] = line.split(": ", 1)[1]
        if client:  # Legg til siste klient
            clients.append(client)
        
        return {"clients": clients}
    
    except subprocess.CalledProcessError as e:
         return {"error": "Error: "}
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

while True:
    wireguard_status = GetWGStatus()
    print("Sendt status...")
    SendToMQTT(os.getenv('mqtt_topic'), wireguard_status)
    time.sleep(resendrate)
