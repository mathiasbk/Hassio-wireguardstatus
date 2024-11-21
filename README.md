# Wireguard Status MQTT Integration

## Overview

This Python script fetches the status of a locally installed Wireguard server and sends the data to an MQTT broker. The goal is to integrate this data into **Home Assistant** to monitor Wireguard server status and statistics in real time.

---

## Features

- Retrieves status information from a Wireguard server running locally.
- Publishes server and client statistics to a configured MQTT broker.
- Designed for seamless integration with **Home Assistant**.

---

## Prerequisites

### Requirements
1. **Python 3.x**: Ensure Python 3.x is installed on your system.
2. **Wireguard**: The script assumes Wireguard is installed and running locally.
3. **MQTT Broker**: An MQTT broker (e.g., Mosquitto) must be set up to receive the data.

### Required Libraries
Install the required libraries using `pip`:

```bash
pip install python-dotenv
pip install paho-mqtt
```

### Usage

Start the script with

```bash
python server.py
```