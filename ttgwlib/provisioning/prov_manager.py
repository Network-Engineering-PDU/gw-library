import logging
import subprocess
import threading
import re

from ttgwlib.events.event import Event

from ttgwlib.node import Node
from ttgwlib.provisioning.provisioner import Provisioner
from ttgwlib.provisioning.filter import ScanFilter
from ttgwlib.events.event import EventType
from ttgwlib.events import time_events
from ttgwlib import commands

class ProvManager:
    def __init__(self, gateway):
        self.logger = logging.getLogger(__name__)
        self.gw = gateway
        self.prov_filter = None
        self.provisioner = Provisioner(self.gw)
        self.scanning = False
        self.provisioning = False
        self.prov_only_one = False
        self.scanned_nodes = []

    def unprov_handler(self, event):
        if event.event_type == EventType.UNPROV_DISC:
            node = Node(event.data["adv_addr"], event.data["uuid"])
            if node not in self.scanned_nodes:
                self.scanned_nodes.append(node)
            # Check if device is stored as provisioned
            if node in self.gw.node_db.get_nodes():
                self.logger.warning("Provisioned device %s announcing " +
                    "as unprovisioned, removing it", node)
                self.gw.node_db.remove_node(node)

            self.logger.info("Unprovisioned device discovered: %s (uuid=%s)",
                    node.mac.hex(), node.uuid.hex())
            if not self.provisioning and self.prov_filter.check(node):
                self.logger.info("New device %s matched scan filter", node)
                self.provision(node)

    def scan_timeout_handler(self, event):
        if event.event_type == EventType.SCAN_TIMEOUT:
            self.stop_scan()
            self.gw.remove_event_handler(self.scan_timeout_handler)

    def start_scan(self, uuid_filters, mac_filters, timeout=0, one=False):
        self.prov_only_one = one
        if self.scanning or self.gw.is_listener():
            return
        self.scanned_nodes = []
        self.scanning = True
        self.prov_filter = ScanFilter(uuid_filters, mac_filters)

        self.logger.info("Starting unprovisioned device scan (timeout=%s, one=%s)",
                timeout, one)

        if timeout > 0:
            time_events.ScanTimeout(timeout, self.gw)
            self.gw.add_event_handler(self.scan_timeout_handler)

        self.gw.add_event_handler(self.unprov_handler)
        msg = commands.ScanStart()
        self.gw.uart.send_msg(msg.serialize())

    def stop_scan(self):
        if not self.scanning:
            return
        self.scanning = False

        msg = commands.ScanStop()
        self.gw.uart.send_msg(msg.serialize())
        self.gw.remove_event_handler(self.unprov_handler)

        if self.scanned_nodes:
            devices = ", ".join(
                f"{node.mac.hex()} (uuid={node.uuid.hex()})"
                for node in self.scanned_nodes
            )
            self.logger.info("Scan stopped. Discovered devices: %s", devices)
        else:
            self.logger.info("Scan stopped. No unprovisioned devices discovered.")
            # Fallback: attempt a short host-side bluetoothctl scan and emit
            # synthetic UNPROV_DISC events for discovered BLE devices. This
            # helps surface generic beacons (MST01 / BeaconX Pro) that the
            # firmware's provisioner may ignore.
            try:
                t = threading.Thread(target=self._host_scan_and_emit,
                                     args=(5,))
                t.daemon = True
                t.start()
            except Exception:
                self.logger.exception("Host scan fallback failed to start")
        self.scanned_nodes = []

    def _host_scan_and_emit(self, scan_time=5):
        """Run a short host-side BLE scan and inject UNPROV_DISC events.

        Attempts multiple scan methods: hcitool lescan, bluetoothctl, hcitool scan.
        
        :param scan_time: seconds to run scan
        """
        seen_macs = set()
        scan_time = int(scan_time)
        
        try:
            # Method 1: Try hcitool lescan (simpler output format)
            self.logger.info("Host fallback: attempt 1 - trying hcitool lescan for %s s", scan_time)
            try:
                cmd = f"timeout {scan_time} hcitool lescan --duplicates"
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True)
                out, _ = proc.communicate(timeout=scan_time+2)
                out = out or ""
                
                self.logger.debug("hcitool lescan output (len=%d): %s...", len(out),
                                 out[:300].replace('\n', ' ') if out else "(empty)")
                
                # Parse lines like "AA:BB:CC:DD:EE:FF (unknown)", "AA:BB:CC:DD:EE:FF BeaconX Pro",
                # or "AA:BB:CC:DD:EE:FF BeaconX Pro -55 dBm" when RSSI is present.
                dev_re = re.compile(r"([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:"
                                   r"[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})")
                
                for line in out.splitlines():
                    if not line.strip() or "LE Scan" in line:
                        continue
                    m = dev_re.search(line)
                    if not m:
                        continue
                    mac = m.group(1).upper()
                    if mac in seen_macs:
                        continue
                    seen_macs.add(mac)
                    rssi = self._parse_rssi_from_line(line)
                    self.logger.debug("hcitool lescan found: %s (rssi=%s) from line: %s",
                                      mac, rssi, line.strip())
                    self._emit_device(mac, rssi)
                
                if seen_macs:
                    self.logger.info("Host fallback: hcitool lescan found %d devices", len(seen_macs))
                    return
            except Exception as e:
                self.logger.debug("hcitool lescan failed: %s", e)
            
            # Method 2: Try bluetoothctl scan with direct shell
            self.logger.info("Host fallback: attempt 2 - trying bluetoothctl for %s s", scan_time)
            try:
                # Run bluetoothctl with explicit timeout and direct scan
                cmd = (
                    f"(echo 'scan on'; sleep {scan_time}; echo 'quit') | "
                    f"timeout {scan_time+2} bluetoothctl 2>&1"
                )
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True)
                out, err = proc.communicate(timeout=scan_time+3)
                out = out or ""
                
                self.logger.debug("bluetoothctl output (len=%d): %s...", len(out),
                                 out[:300].replace('\n', ' ') if out else "(empty)")
                
                # bluetoothctl prints lines like "[NEW] Device AA:BB:CC:DD:EE:FF Name"
                # Some builds may include RSSI information in the same scan output.
                dev_re = re.compile(r"Device\s+([0-9A-Fa-f:]{17})")
                for line in out.splitlines():
                    if not self._is_probably_ble_device(line):
                        continue
                    m = dev_re.search(line)
                    if not m:
                        continue
                    mac = m.group(1).upper()
                    if mac in seen_macs:
                        continue
                    seen_macs.add(mac)
                    rssi = self._parse_rssi_from_line(line)
                    self.logger.debug("bluetoothctl found: %s (rssi=%s) from line: %s",
                                      mac, rssi, line.strip())
                    self._emit_device(mac, rssi)
                
                if seen_macs:
                    self.logger.info("Host fallback: bluetoothctl found %d devices", len(seen_macs))
                    return
            except Exception as e:
                self.logger.debug("bluetoothctl failed: %s", e)
            
            # Method 3: Try hcitool scan (generic BLE discovery, slower)
            self.logger.info("Host fallback: attempt 3 - trying hcitool scan for %s s", scan_time)
            try:
                cmd = f"timeout {scan_time} hcitool scan"
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True)
                out, err = proc.communicate(timeout=scan_time+2)
                out = out or ""
                
                self.logger.debug("hcitool scan output (len=%d): %s...", len(out),
                                 out[:300].replace('\n', ' ') if out else "(empty)")
                
                dev_re = re.compile(r"([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:"
                                   r"[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})")
                for line in out.splitlines():
                    if not line.strip() or "Scanning" in line:
                        continue
                    m = dev_re.search(line)
                    if not m:
                        continue
                    mac = m.group(1).upper()
                    if mac in seen_macs:
                        continue
                    seen_macs.add(mac)
                    self.logger.debug("hcitool scan found: %s", mac)
                    self._emit_device(mac)
                
                if seen_macs:
                    self.logger.info("Host fallback: hcitool scan found %d devices", len(seen_macs))
                    return
            except Exception as e:
                self.logger.debug("hcitool scan failed: %s", e)
            
            self.logger.info("Host fallback: all scan methods completed, %d unique devices found", len(seen_macs))
                
        except Exception:
            self.logger.exception("Error during host fallback bluetooth scan")

    def _parse_rssi_from_line(self, line):
        if not line:
            return None
        # Prefer explicit RSSI labels, then dBm, then numeric trailing parentheses.
        patterns = [
            r"RSSI:\s*(-?\d+)",
            r"(-?\d+)\s*dBm",
            r"\((-?\d+)\)\s*$",
        ]
        for pat in patterns:
            m = re.search(pat, line, re.IGNORECASE)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    return None
        return None

    def _is_probably_ble_device(self, line):
        if not line:
            return False
        lower = line.lower()
        blacklist = [
            'tv', 'phone', 'headphone', 'headset', 'speaker', 'audio',
            'keyboard', 'mouse', 'laptop', 'desktop', 'tablet', 'watch',
            'camera', 'printer', 'car', 'remote', 'gamepad', 'smartphone',
            'console', 'bluetooth', 'samsung', 'sony', 'lg'
        ]
        for token in blacklist:
            if token in lower:
                return False
        return True

    def _emit_device(self, mac_str, rssi=None):
        """Emit a synthetic UNPROV_DISC event for a discovered MAC address.
        
        :param mac_str: MAC address string like "AA:BB:CC:DD:EE:FF"
        :param rssi: Optional RSSI value (in dBm, typically -100 to 0)
        """
        try:
            adv_addr = bytes.fromhex(mac_str.replace(':', ''))
            
            data = {
                "uuid": None,
                "rssi": rssi,
                "gatt_supported": False,
                "adv_addr_type": 0,
                "adv_addr": adv_addr,
            }
            evt = Event(EventType.UNPROV_DISC, data, self.gw)
            self.gw.event_handler.add_event(evt)
            self.logger.info("Host fallback: emitted UNPROV_DISC for %s (rssi=%s)", 
                           mac_str, rssi)
        except Exception:
            self.logger.exception("Error emitting device %s", mac_str)

    def provision(self, node):
        if self.provisioning:
            self.logger.warning("A node is already being provisioned")
            return
        msg = commands.ScanStop()
        self.gw.uart.send_msg(msg.serialize())
        self.provisioning = True
        self.provisioner.provision(node)

    def end_provision(self):
        self.provisioning = False
        if self.prov_only_one:
            self.stop_scan()
        if self.scanning:
            msg = commands.ScanStart()
            self.gw.uart.send_msg(msg.serialize())
