import time
import struct
import logging
import threading
from collections import OrderedDict
from ttgwlib.platform.exception import GatewayError

import ttgwlib.events.mesh_events as events
from ttgwlib import commands


APP_KEY = bytes.fromhex("4F68AD85D9F48AC8589DF665B6B49B8A")


class GroupAddress:
    """Pub/Sub group addresses."""
    WAKE = 49156
    NRFTEMP = 49400


class HandleManager:
    """ HandleManager is responsible for managing the device and address handles
    of the nodes for the Bluetooth Mesh protocol.

    :param dev_manager: The device manager responsible for sending commands and
        managing devices.
    :type dev_manager: :class:`~ttgwlib.dev_manager.DevManager`
    """
    MAX_DEVKEYS = 10
    MAX_ADDRESSES = 30
    def __init__(self, dev_manager):
        self.dev_manager = dev_manager
        self.netkey = None
        self.appkey = None
        self.devkeys = OrderedDict() # Dict[devkey, key_handle]
        self.devkeys_addr = [] # List[address]

        self.wake_addr = None
        self.nrftemp_addr = None
        self.addresses = OrderedDict() # Dict[address, address_handle]

    def get_devkey_handle(self, node):
        """ Retrieve or create a handle for the device key of a node.

        :param node: The node object containing the device key and address
            information.
        :type node: :class:`~ttgwlib.node.Node`

        :return: The handle associated with the device key.
        :rtype: integer
        """
        if node.devkey in self.devkeys:
            return self.devkeys[node.devkey]
        if node.unicast_addr in self.devkeys_addr:
            index = self.devkeys_addr.index(node.unicast_addr)
            key = list(self.devkeys)[index]
            key_handle = self.devkeys[key]
            self.devkeys_addr.pop(index)
            del self.devkeys[key]
            msg = commands.DevkeyDelete(key_handle)
            self.dev_manager.send_cmd_wait_rsp(msg)
        elif len(self.devkeys) >= self.MAX_DEVKEYS:
            _, old_key_handle = self.devkeys.popitem(last=False)
            self.devkeys_addr.pop(0)
            msg = commands.DevkeyDelete(old_key_handle)
            self.dev_manager.send_cmd_wait_rsp(msg)
        msg = commands.DevkeyAdd(node.unicast_addr, node.netkey_index,
            node.devkey)
        rsp = self.dev_manager.send_cmd_wait_rsp(msg)
        key_handle = struct.unpack("<H", rsp["rsp_data"])[0]
        self.devkeys[node.devkey] = key_handle
        self.devkeys_addr.append(node.unicast_addr)
        return key_handle

    def get_address_handle(self, address):
        """ Retrieve or create a handle for a specific address.

        :param address: The address for which the handle is required.
        :type address: integer

        :return: The handle associated with the address.
        :rtype: integer
        """
        if address in self.addresses:
            return self.addresses[address]
        if len(self.addresses) >= self.MAX_ADDRESSES:
            _, old_addr_handle = self.addresses.popitem(last=False)
            msg = commands.AddrPublicationRemove(old_addr_handle)
            self.dev_manager.send_cmd_wait_rsp(msg)
        msg = commands.AddrPublicationAdd(address)
        rsp = self.dev_manager.send_cmd_wait_rsp(msg)
        addr_handle = struct.unpack("<H", rsp["rsp_data"])[0]
        self.addresses[address] = addr_handle
        return addr_handle


class DeviceManager:
    """ DeviceManager is responsible for managing device operations including
    initializtion, configuration, connection checking, and command handling.
    """
    SEQ_BLOCK = 100
    dev_id = 0

    def __init__(self, gateway, seq_number_file, remote=False):
        """ Initializes DeviceManager

        :param gateway: The gateway object used for communication with the
            device.
        :type gateway: :class:`~ttgwlib.gateway.Gateway`

        :param seq_number_file: File path for storing and retrieving the
            sequence number.
        :type seq_number_file: str

        :param remote: Boolean flag indicating whether the device manager
            operates in remote mode.
        :type remote: bool
        """
        self.logger = logging.getLogger(__name__)
        self.gw = gateway
        self.seq_number_file = seq_number_file
        self.remote = remote
        self.handles = HandleManager(self)

        self.dev_started = False
        self.clean = True
        self.check_connection_flag = False

        #TODO Dummy cache size, this is not used anymore
        self.cache_size = 0x7000

        self.dev_id = DeviceManager.dev_id
        DeviceManager.dev_id += 1

        self.cmd_opcode_wait = None
        self.cmd_complete = False
        self.cmd_response = None

        self.evt_thd = None

    def dev_event_handler(self, event):
        if event.event_type == events.EventType.DEV_RESET:
            if self.evt_thd and self.evt_thd.is_alive:
                raise GatewayError("Gateway reinicialization too fast")

            self.evt_thd = threading.Thread(target=self.config_device,
                    name=f"DevManager {self.dev_id}")
            self.evt_thd.start()

        elif event.event_type == events.EventType.SEQ_UPDATE:
            with open(self.seq_number_file, "w") as f:
                f.write(str(event.data["seq_number"]))

        elif event.event_type == events.EventType.ECHO:
            if event.data["echo"] == bytes.fromhex("0204FF"):
                self.check_connection_flag = True

        elif event.event_type == events.EventType.RSP_EVENT:
            if event.data["opcode"] == self.cmd_opcode_wait:
                self.cmd_response = event.data
                self.cmd_complete = True

        elif event.event_type == events.EventType.RSP_SEND:
            if self.cmd_opcode_wait == 0xab:
                self.cmd_response = event.data
                self.cmd_complete = True

    def send_cmd_wait_rsp(self, cmd):
        """ Send a command and wait for the response.

        Can not be used in event callback (blocks evt handler thread).

        :param cmd: The command object to be sent.
        :type cmd: :class:`~ttgwlib.commands.CommandPacket`

        :return: The response received for the command.
        :rtype: dict
        """
        #TODO timeout
        self.cmd_complete = False
        self.cmd_opcode_wait = cmd.get_opcode()
        self.gw.uart.send_msg(cmd.serialize())
        while not self.cmd_complete:
            time.sleep(0.1)
        return self.cmd_response

    def check_connection(self):
        """ Check the connection status by sending an echo message.

        :return: Boolean indicating whether the connection check was successful.
        :rtype: bool
        """
        self.check_connection_flag = False
        msg = commands.Echo(bytes.fromhex("0204FF"))
        self.gw.uart.send_msg(msg.serialize())
        n = 0
        # TODO: do it with lock
        while not self.check_connection_flag:
            if n < 10:
                time.sleep(0.50)
                n += 1
            else:
                break
        return self.check_connection_flag

    def reset_device(self):
        """ Reset the device by sending a reset command.
        """
        msg = commands.Reset()
        self.gw.uart.send_msg(msg.serialize())

    def start(self):
        if not self.clean:
            raise GatewayError("Dev manager can not start twice")

        self.gw.add_event_handler(self.dev_event_handler)

        self.clean = False
        self.dev_started = False

        if not self.remote:
            self.start_device()

    def start_device(self):
        """ Start the device by resetting it and waiting until it is fully
        started.
        """

        self.reset_device()

        while not self.dev_started:
            pass

    def config_device(self):
        """ Configure the device, including setting addresses, sequence numbers,
        and adding keys.
        """
        self.logger.info("Configuring gateway")

        #msg = commands.AdvertisingAddressGet()
        #self.send_cmd_wait_rsp(msg)

        msg = commands.StateClear()
        self.send_cmd_wait_rsp(msg)

        # Set unicast address
        self.logger.debug("Setting gateway unicast address to %d",
            self.gw.node_db.get_address())
        msg = commands.AddrLocalUnicastSet(self.gw.node_db.get_address(), 1)
        self.send_cmd_wait_rsp(msg)

        # Consistent sequence number
        try:
            with open(self.seq_number_file) as f:
                seq = int(f.read())
            seq = self.SEQ_BLOCK * (seq // self.SEQ_BLOCK + 1)
        except (FileNotFoundError, ValueError):
            seq = 0
        with open(self.seq_number_file, "w") as f:
            f.write(str(seq))
        msg = commands.SetNetState(0, 0, 0, seq)
        self.send_cmd_wait_rsp(msg)

        self.logger.debug("Adding keys")
        # Netkey
        msg = commands.SubnetAdd(0, self.gw.node_db.get_netkey())
        rsp = self.send_cmd_wait_rsp(msg)
        self.handles.netkey = struct.unpack("<H", rsp["rsp_data"])[0]
        # Appkey
        msg = commands.AppkeyAdd(0, 0, APP_KEY)
        rsp = self.send_cmd_wait_rsp(msg)
        self.handles.appkey = struct.unpack("<H", rsp["rsp_data"])[0]

        # WakeUp subscription
        self.logger.debug("Wake Up subscription (%d)", GroupAddress.WAKE)
        msg = commands.AddrSubscriptionAdd(GroupAddress.WAKE)
        rsp = self.send_cmd_wait_rsp(msg)
        self.handles.wake_addr = struct.unpack("<H", rsp["rsp_data"])[0]

        # NRFTemp subscription
        self.logger.debug("NRFTemp subscription (%d)", GroupAddress.NRFTEMP)
        msg = commands.AddrSubscriptionAdd(GroupAddress.NRFTEMP)
        rsp = self.send_cmd_wait_rsp(msg)
        self.handles.nrftemp_addr = struct.unpack("<H", rsp["rsp_data"])[0]

        self.dev_started = True

    def stop(self):
        if not self.remote:
            self.stop_device()

        self.dev_started = False

        if self.evt_thd is None:
            self.logger.warning(
                "Dev manager stopped without finishing initialization")

        if self.evt_thd and self.evt_thd.is_alive():
            raise GatewayError(
                "Cannot stop dev_manager while configuring device")

        self.gw.remove_event_handler(self.dev_event_handler)

    def stop_device(self):
        """ Stop the device by removing subscriptions and resetting it.
        """
        msg = commands.AddrSubscriptionRemove(self.handles.wake_addr)
        self.gw.uart.send_msg(msg.serialize())
        msg = commands.AddrSubscriptionRemove(self.handles.nrftemp_addr)
        self.gw.uart.send_msg(msg.serialize())
        self.reset_device()

    #TODO unused
    def clear_replay_cache(self, unicast_address):
        """ Clears reply cache.

        Now it removes msg cache (replay cache does not exist inside nRF
        anymore).
        """
        msg = commands.ClearNodeReplayCache(unicast_address)
        self.gw.uart.send_msg(msg.serialize())
