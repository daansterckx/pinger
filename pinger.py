from flask import Flask, render_template, request, redirect, url_for
import os
import time
import subprocess
import threading
import json
import requests

app = Flask(__name__)

# File to store the devices
DEVICES_FILE = 'devices.json'
DISCORD_WEBHOOK_URL = ''  # Replace with your Discord webhook URL

# Load devices from the file
def load_devices():
    if os.path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, 'r') as f:
            devices = json.load(f)
            # Ensure all devices have the alert flag
            return [(device[0], device[1], device[2] if len(device) > 2 else False) for device in devices]
    return []

# Save devices to the file
def save_devices():
    with open(DEVICES_FILE, 'w') as f:
        json.dump(devices, f)

# List of tuples containing IP addresses or hostnames, their names, and alert flag
devices = load_devices()
device_statuses = []

def ping_device(device, name, alert):
    try:
        output = subprocess.check_output(["ping", "-c", "1", "-W", "1", device], stderr=subprocess.STDOUT, universal_newlines=True)
        if "ttl=" in output.lower():
            return f"{name} ({device}) is up"
        else:
            if alert:
                send_discord_alert(name, device)
            return f"{name} ({device}) is down"
    except subprocess.CalledProcessError:
        if alert:
            send_discord_alert(name, device)
        return f"{name} ({device}) is down"

def send_discord_alert(name, device):
    message = f"Alert: {name} ({device}) is down!"
    payload = {
        "content": message
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def ping_all_devices():
    global device_statuses
    device_statuses = [ping_device(device, name, alert) for device, name, alert in devices]
    print(f"Device statuses: {device_statuses}")  # Debugging statement

@app.route('/')
def index():
    ping_all_devices()  # Ensure statuses are updated before rendering
    return render_template('index.html', device_statuses=device_statuses, devices=devices, zip=zip)

@app.route('/add', methods=['POST'])
def add_device():
    ip = request.form['ip']
    name = request.form['name']
    alert = 'alert' in request.form
    devices.append((ip, name, alert))
    save_devices()  # Save devices to the file
    ping_all_devices()  # Update device statuses after adding a new device
    return redirect(url_for('index'))

@app.route('/refresh', methods=['POST'])
def refresh():
    ping_all_devices()
    return redirect(url_for('index'))

@app.route('/toggle_alert/<int:index>', methods=['POST'])
def toggle_alert(index):
    devices[index] = (devices[index][0], devices[index][1], not devices[index][2])
    save_devices()  # Save devices to the file
    return redirect(url_for('index'))

@app.route('/remove/<int:index>', methods=['POST'])
def remove_device(index):
    devices.pop(index)
    save_devices()  # Save devices to the file
    ping_all_devices()  # Update device statuses after removing a device
    return redirect(url_for('index'))

def background_pinger():
    while True:
        ping_all_devices()
        time.sleep(3600)  # Ping every hour

if __name__ == "__main__":
    threading.Thread(target=background_pinger, daemon=True).start()
    app.run(host='0.0.0.0', port=80, debug=True)