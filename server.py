import os
import subprocess
import paho.mqtt.client as mqtt
import time
from dotenv import load_dotenv

load_dotenv()


## Config
resendrate = 5 

##Home assistant config
#mqtt_broker = "<MQTT_BROKER_ADRESSE>"
#mqtt_port = 1883
#mqtt_topic = "home/wireguard/status"
#mqtt_username = "<MQTT_USERNAME>"
#mqtt_password = "<MQTT_PASSWORD>"
#mqtt_broker = "192.168.10.180"
#mqtt_port = 1883
#mqtt_topic = "home/wireguard/status"
#mqtt_username = "mqtt-plejd"
#mqtt_password = "mqtt-plejd"


# Send status to MQTT
def SendToMQTT(topic, message):
    client = mqtt.Client()
    client.username_pw_set(os.getenv('mqtt_username'), os.getenv('mqtt_password'))
    client.connect(os.getenv('mqtt_broker'), int(os.getenv('mqtt_port', 1883)))
    client.publish(topic, message)
    client.disconnect()

def GetWGStatus():
    try:
        status = subprocess.run(['wg', 'show'], capture_output=True, text=True, check=True)
        output = status.stdout
        return output
    
    except subprocess.CalledProcessError as e:
        return "Error: " + str(e)
    except FileNotFoundError as e:
        return "Wireguard not found. Are you sure it is installed?"


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
