#!/usr/bin/env python3
import subprocess
import time
import re
import os
import sys
import getpass
from prometheus_client import start_http_server, Gauge, Counter

# --- Identity Logic ---
def log_identity():
    try:
        print(f"--- Identity Scan ---")
        print(f"User: {getpass.getuser()} (UID: {os.getuid()})")
        print(f"GIDs: {os.getgroups()}")
        print(f"CWD: {os.getcwd()}")
        print(f"---------------------")
        sys.stdout.flush()
    except Exception as e:
        print(f"Identity log failed: {e}")

def set_process_name(name):
    try:
        import setproctitle
        setproctitle.setproctitle(name)
    except ImportError:
        try:
            import ctypes
            libc = ctypes.CDLL('libc.so.6')
            libc.prctl(15, name.encode('utf-8'), 0, 0, 0)
        except Exception:
            pass

# --- Metrics Definitions ---
PREFIX = "hostapd_"
AP_INFO = Gauge(f'{PREFIX}ap_info', 'Hostapd AP info', ['interface', 'ssid', 'channel', 'bssid'])
STA_COUNT = Gauge(f'{PREFIX}ap_num_stations', 'Active stations', ['interface'])
STA_SIGNAL = Gauge(f'{PREFIX}sta_signal_dBm', 'Signal strength', ['interface', 'mac'])
STA_TX_BYTES = Counter(f'{PREFIX}sta_tx_bytes_total', 'TX bytes', ['interface', 'mac'])
STA_RX_BYTES = Counter(f'{PREFIX}sta_rx_bytes_total', 'RX bytes', ['interface', 'mac'])
STA_TX_RATE = Gauge(f'{PREFIX}sta_tx_rate_kbps', 'TX bitrate', ['interface', 'mac'])
STA_RX_RATE = Gauge(f'{PREFIX}sta_rx_rate_kbps', 'RX bitrate', ['interface', 'mac'])
STA_CONNECTED_TIME = Gauge(f'{PREFIX}sta_connected_seconds', 'Conn duration', ['interface', 'mac'])
STA_INACTIVE = Gauge(f'{PREFIX}sta_inactive_seconds', 'Time since last activity', ['interface', 'mac'])
STA_ASSOC = Counter(f'{PREFIX}sta_associations_total', 'Total association events', ['interface', 'mac'])

last_seen_duration = {}

class HostapdCollector:
    def __init__(self, ctrl_dir):
        self.ctrl_dir = ctrl_dir
        self.interface = None
        self.last_check = 0

    def _run_cli(self, command):
        try:
            cmd = ["hostapd_cli", "-p", self.ctrl_dir]
            if self.interface: cmd.extend(["-i", self.interface])
            cmd.append(command)
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
            return res.stdout
        except Exception as e:
            print(f"CLI Error [{command}]: {e}")
            return None

    def find_interface(self):
        if not os.path.exists(self.ctrl_dir): return None
        ifaces = os.listdir(self.ctrl_dir)
        if ifaces:
            self.interface = ifaces[0]
            return self.interface
        return None

    def update(self):
        if not self.interface or (time.time() - self.last_check > 60):
            self.find_interface()
            self.last_check = time.time()

        if not self.interface: return

        # Status / AP Stats
        status = self._run_cli("status")
        if status:
            data = dict(re.findall(r'^([^=]+)=(.*)$', status, re.MULTILINE))
            count = data.get('num_sta[0]') or data.get('num_sta', 0)
            STA_COUNT.labels(interface=self.interface).set(count)
            AP_INFO.labels(
                interface=self.interface,
                ssid=data.get('ssid[0]') or data.get('ssid', 'unknown'),
                channel=data.get('channel', '0'),
                bssid=data.get('bssid[0]') or data.get('bssid', 'unknown')
            ).set(1)

        # Station Stats
        all_sta = self._run_cli("all_sta")
        if all_sta:
            stations = re.split(r'^([0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2})',
                               all_sta, flags=re.MULTILINE)
            for i in range(1, len(stations), 2):
                mac = stations[i]
                s = dict(re.findall(r'^([^=]+)=(.*)$', stations[i+1], re.MULTILINE))
                STA_SIGNAL.labels(interface=self.interface, mac=mac).set(s.get('signal', 0))
                STA_CONNECTED_TIME.labels(interface=self.interface, mac=mac).set(s.get('connected_time', 0))
                STA_TX_RATE.labels(interface=self.interface, mac=mac).set(s.get('tx_rate', 0))
                STA_RX_RATE.labels(interface=self.interface, mac=mac).set(s.get('rx_rate', 0))
                STA_TX_BYTES.labels(interface=self.interface, mac=mac)._value.set(float(s.get('tx_bytes', 0)))
                STA_RX_BYTES.labels(interface=self.interface, mac=mac)._value.set(float(s.get('rx_bytes', 0)))

                inactive_s = float(s.get('inactive_ms', 0)) / 1000.0
                STA_INACTIVE.labels(interface=self.interface, mac=mac).set(inactive_s)

                current_duration = int(s.get('connected_time', 0))
                previous_duration = last_seen_duration.get(mac, 0)

                if mac not in last_seen_duration or current_duration < previous_duration:
                    STA_ASSOC.labels(interface=self.interface, mac=mac).inc()

                last_seen_duration[mac] = current_duration

def main():
    log_identity()
    set_process_name("prometheus-hostapd-exporter")

    port = int(os.environ.get("EXPORTER_PORT", 9551))
    addr = os.environ.get("EXPORTER_ADDR", "0.0.0.0")
    ctrl = os.environ.get("HOSTAPD_CTRL_DIR", "/run/hostapd")
    interval = int(os.environ.get("SCRAPE_INTERVAL", 5))

    collector = HostapdCollector(ctrl)
    print(f"Starting Hostapd Exporter on {addr}:{port}...")
    start_http_server(port, addr=addr)

    while True:
        collector.update()
        time.sleep(interval)

if __name__ == '__main__':
    main()

