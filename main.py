import pywifi
import socket
import json
import os
import platform
import time

port = 5555

def launch_hotspot(ifname):
    assert platform.system().lower() == "linux", "Hotspot can be started only on linux"
    os.system(f"""nmcli connection add ifname {ifname}\
            type wifi autoconnect yes wifi.ssid APTest\
            ip4 192.168.0.1/24 gw4 192.168.0.1\
            wifi.mode ap\
            ipv4.method shared ipv6.method disabled\
            con-name Hotspot""")
    
def stop_hotspot():
    os.system("nmcli connection delete Hotspot")

def get_wifi_interface():
    wifi = pywifi.PyWiFi()
    interfaces = [i for i in wifi.interfaces() if not "p2p-dev" in i.name()]
    return interfaces[0]

def scan_wifi(iface):
    iface.scan()
    results = iface.scan_results()
    return results

def format_scan_results(results):
    formatted_results = dict()
    for p in results:
        if p.ssid == "":
            continue

        # On récupère la meilleure valeur de force de signal
        if p.signal == 0:
            continue
        signal = p.signal
        if p.ssid in formatted_results:
            signal = max(formatted_results[p.ssid], p.signal)
        formatted_results[p.ssid] = signal
    print(formatted_results)
    return formatted_results

def connect_to_network(ssid, key):
    # On force le rescan des réseaux Wifi (la sortie du mode Hotspot juste avant peut être source d'erreur sinon)
    os.system("nmcli device wifi rescan")
    time.sleep(2)
    os.system(f"nmcli device wifi connect {ssid} password {key}")


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    iface = get_wifi_interface()
    launch_hotspot(iface.name())

    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', port))
    s.listen(1)
    print(f"Listening on port {port} ...")
    while True:
        (conn, address) = s.accept()
        print("Received a connection")
        with conn:
            print("Scanning...")
            ap_profiles = scan_wifi(iface)
            formatted_results = format_scan_results(ap_profiles)
            conn.sendall(json.dumps(formatted_results).encode("utf-8"))
            while True:
                buff = conn.recv(512)

                content = buff.decode("utf-8")
                
                try:
                    res = json.loads(content)  # dict {<SSID>: <key>}
                except:
                    continue
                ssid_received = list(res.keys())[0]
                key_received = res[ssid_received]

                print(res)
                conn.sendall(json.dumps({ssid_received: True}).encode("utf-8"))

                # Connect to Wifi
                stop_hotspot()
                connect_to_network(ssid_received, key_received)
