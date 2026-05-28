import logging

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
        self.scanned_nodes = []

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
