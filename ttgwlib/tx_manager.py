import queue
import threading
import logging

from ttgwlib import commands
from ttgwlib.events.event import EventType


logger = logging.getLogger(__name__)


class TxManager:
    """ TxManager is responsible for managing the sending process of messages
    from the gateway to the nodes of the network.

    It uses the device manager :class:`~ttgwlib.dev_manager.DevManager` to
    send messages and implements two queues: one for sending regular messages
    and one for sending low priority messages.
    """
    TTL = 127
    FORCE_SEGMENTED = False
    TRANSMIC_SIZE = 0
    tx_id = 0

    def __init__(self, gateway):
        """ Initialize the TxManager with the given gateway.

        :param gateway: The gateway instance associated with this TxManager.
        :type gateway: :class:`~ttgwlib.gateway.Gateway`
        """

        self.gw = gateway
        self.tx_id = TxManager.tx_id
        TxManager.tx_id += 1
        self.handles = self.gw.dev_manager.handles
        self.gw.add_event_handler(self.rsp_handler)
        self.gw.add_event_handler(self.sent_handler)

        # Size 10 already fails on a nRF52832. 5 works, 3 for safety
        self.semaphore = threading.Semaphore(3)
        self.pending = set()

        self.send_queue = queue.Queue()
        self.low_priority_queue = queue.Queue()
        self.running = True
        self.tx_thd = threading.Thread(target=self._run,
            name=f"TxManager {self.tx_id}")
        self.tx_thd.start()

    def rsp_handler(self, event):
        """ Handle response events related to message sending.

        :param event: The event object containing the response details.
        :type event: :class:`~ttgwlib.events.event.Event`
        """
        if event.event_type == EventType.RSP_SEND:
            if event.data["result"] == 0:
                self.pending.add(event.data["token"])
            else:
                logger.warning("Send failed: %d", event.data["result"])
                self.semaphore.release()

    def sent_handler(self, event):
        """ Handle completion events for transmitted messages.

        :param event: The event object containing the completion details.
        :type event: :class:`~ttgwlib.events.event.Event`
        """
        if event.event_type == EventType.MESH_TX_COMPLETE:
            if event.data["token"] in self.pending:
                self.pending.remove(event.data["token"])
                self.semaphore.release()

    def send_node(self, data, node):
        """ Queue a message to be sent to a specific node.

        :param data: The message data to be sent.
        :type data: bytearray

        :param node: The node object representing the destination.
        :type node: class:`~ttgwlib.node.Node`
        """
        if not self.gw.is_listener() and not self.gw.is_provisioner_mode():
            self.send_queue.put((data, node))

    def send_addr(self, data, addr, low_priority=False):
        """ Queue a message to be sent to a specific address.

        :param data: The message data to be sent.
        :type data: bytearray

        :param addr: The destination address.
        :type addr: integer

        :param low_priority: Boolean flag indicating whether the message is low
            priority.
        :type low_priority: bool
        """
        if low_priority:
            self.low_priority_queue.put((data, addr))
        else:
            self.send_queue.put((data, addr))

    def _run(self):
        """ Main loop function to process messages from both send and low
        priority queues.

        Continuously processes messages from both send and low priority queues,
        ensuring proper semaphore acquisition before sending messages.
        """
        while self.running:
            try:
                data, dst = self.send_queue.get(timeout=0.1)
            except queue.Empty:
                try:
                    data, dst = self.low_priority_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

            while not self.semaphore.acquire(timeout=1):
                if not self.running:
                    break

            if isinstance(dst, int):
                self._send_addr(data, dst)
            else:
                self._send_node(data, dst)

    def _send_node(self, data, node):
        """ Send a message to a specific node.

        :param data: The message data to be sent.
        :type data: bytearray

        :param node: The node object representing the destination.
        :type node: class:`~ttgwlib.node.Node`
        """
        key_handle = self.handles.get_devkey_handle(node)
        addr_handle = self.handles.get_address_handle(node.unicast_addr)

        msg = commands.PacketSend(key_handle, self.gw.node_db.get_address(),
            addr_handle, self.TTL, self.FORCE_SEGMENTED, self.TRANSMIC_SIZE,
            data)
        self.gw.dev_manager.send_cmd_wait_rsp(msg)

    def _send_addr(self, data, addr):
        """ Send a message to a specific address.

        :param data: The message data to be sent.
        :type data: bytearray

        :param addr: The destination address.
        :type addr: integer
        """
        addr_handle = self.handles.get_address_handle(addr)

        msg = commands.PacketSend(self.handles.appkey,
            self.gw.node_db.get_address(), addr_handle, self.TTL,
            self.FORCE_SEGMENTED, self.TRANSMIC_SIZE, data)
        self.gw.dev_manager.send_cmd_wait_rsp(msg)

    def stop(self):
        """ Stop the TxManager and terminate the processing thread.
        """
        self.running = False
        if self.tx_thd and self.tx_thd.is_alive():
            self.tx_thd.join(timeout=10)
            if self.tx_thd.is_alive():
                logger.warning("Failed to join TX thread in time")
