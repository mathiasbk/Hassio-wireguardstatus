import os
import subprocess

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

wireguard_status = GetWGStatus()
print("Status: " + wireguard_status)