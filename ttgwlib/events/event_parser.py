import struct
import logging
import threading

from ttgwlib.events import mesh_events
from ttgwlib.events import model_events
from ttgwlib.events.uart_events import UartDisconnection


logger = logging.getLogger(__name__)


MESH_EVENT_OPCODES = {
    0x81: mesh_events.DeviceStarted,
    0x82: mesh_events.EchoRsp,
    0x84: mesh_events.CmdResponse,
    0x8A: mesh_events.Application,
    0xC0: mesh_events.ProvUnprovisionedReceived,
    0xC3: mesh_events.ProvCapsReceived,
    0xC6: mesh_events.ProvAuthRequest,
    0xC7: mesh_events.ProvEcdhRequest,
    0xC9: mesh_events.ProvFailed,
    0xC5: mesh_events.ProvComplete,
    0xC2: mesh_events.ProvLinkClosed,
    0xC1: mesh_events.ProvLinkEstablished,
    0xD2: mesh_events.MeshTxComplete,
}

MODEL_EVENT_OPCODES = {
    0x804A: model_events.NodeReset,
    0xC00000: model_events.WakeNotify,
    0xC30000: model_events.WakeAckSleep,
    0xC40000: model_events.WakeAckWait,
    0xC80000: model_events.WakeAckAlive,
    0xC50000: model_events.WakeReset,
    0xC00200: model_events.TempData,
    0xC10200: model_events.IaqData,
    0xC30200: model_events.IaAck,
    0xC40200: model_events.TempDataReliable,
    0xC60200: model_events.Co2Data,
    0xC80200: model_events.TempConfigAck,
    0xCA0200: model_events.TempCalibAck,
    0xCC0200: model_events.TempCalResetAck,
    0xCD0200: model_events.TempHeaterNotify,
    0xC00400: model_events.BatData,
    0xC00600: model_events.TapNotify,
    0xC20600: model_events.TapAckConf,
    0xC10800: model_events.LightAck,
    0xC00A00: model_events.DatetimeReq,
    0xC20A00: model_events.DatetimeAck,
    0xC10C00: model_events.TaskAck,
    0xC30C00: model_events.TaskDeleteAck,
    0xC50C00: model_events.TaskDeleteOpAck,
    0xC70C00: model_events.TaskData,
    0xC80C00: model_events.TaskGetTasksAck,
    0xCD0C00: model_events.TaskChangeAck,
    0xC11400: model_events.PowerAck,
    0xC01600: model_events.HwmData,
    0xC21600: model_events.HwmAck,
    0xC00E00: model_events.RssiNeighbrData,
    0xC20E00: model_events.RssiNeighbrAck,
    0xC40E00: model_events.RssiStatusAck,
    0xC50E00: model_events.RssiPing,
    0xC60E00: model_events.RssiPingAck,
    0xC11200: model_events.OtaVersionAck,
    0xC31200: model_events.OtaStatusAck,
    0xC51200: model_events.OtaStoreAck,
    0xC71200: model_events.OtaRelayAck,
    0xC11800: model_events.BeaconStartAck,
    0xC31800: model_events.BeaconStopAck,
    0xC21A00: model_events.TransportRecv,
    0xC31A00: model_events.TransportFrStart,
    0xC41A00: model_events.TransportFrData,
    0xC51A00: model_events.TransportFrEnd,
    0xC01C00: model_events.PwmtData,
    0xC21C00: model_events.PwmtConfigAck,
    0xC41C00: model_events.PwmtConvAck,
    0xC61E00: model_events.OutputCmdAck,
    0xC71E00: model_events.OutputCmdNack,
    0xC81E00: model_events.OutputAck,
}


class EventParser:
    """ EventParser is responsible for processing every incoming UART messages,
    deserializing them and dispatching them to the event handler.
    """
    parser_id = 0
    def __init__(self, gateway):
        """ Initialize the event parser.

        :param gateway: The gateway instance for which the event parser is being
            created.
        :type gateway: :class:`~ttgwlib.gateway.Gateway`
        """
        self.gw = gateway
        self.uart = self.gw.uart
        self.event_handler = self.gw.event_handler
        self.running = threading.Event()
        self.parser_id = EventParser.parser_id
        self.rx_thread = None
        EventParser.parser_id += 1

    def start(self):
        """ Start the event parser thread.

        This method starts a new thread to process incoming UART messages.
        """
        self.running.set()
        self.rx_thread = threading.Thread(
            target=self.rx_process, name=f"EvtParser {self.parser_id}")
        self.rx_thread.start()
        logger.debug("Event parser start")

    def stop(self):
        """ Stop the event parser thread.

        This method stops the UART message processing thread and waits for it to
        finish.
        """
        self.running.clear()
        if self.rx_thread and self.rx_thread.is_alive():
            self.rx_thread.join(timeout=10)
            if self.rx_thread.is_alive():
                logger.warning("Failed to join rx_thread in time")
        logger.debug("Event parser stop")

    def rx_process(self):
        """ Process incoming UART messages.

        This method runs in a loop, fetching messages from the UART and
        dispatching them to the appropriate handlers.
        """
# pylint: disable=bare-except
        try:
            start = bytearray.fromhex("048102")
            msg = bytearray(5)
            # Ignore incoming messages until the start message is received
            while start != msg[:3]:
                if not self.running.is_set():
                    return
                rx_byte = self.uart.get_byte(1)
                if rx_byte:
                    msg = msg[1:5] + rx_byte
            self.process_packet(msg)

            while self.running.is_set():
                if not self.uart.is_connected():
                    event = UartDisconnection(self.gw)
                    self.event_handler.add_event(event)
                    break
                msg = bytearray()
                msg += self.uart.get_byte(1)
                if msg:
                    while len(msg) < msg[0] + 1:
                        if not self.running.is_set():
                            return
                        msg += self.uart.get_byte(1)
                    self.process_packet(msg)
        except:
            logger.exception("Error in rx_process")
# pylint: enable=bare-except

    def process_packet(self, msg):
        """ Process a received packet.

        :param msg: The received message as a bytearray.
        :type msg: bytearray
        """
        logger.log(9, f"RX: {msg.hex()}")
        try:
            event = self.deserialize(msg)
            if event:
                self.event_handler.add_event(event)
        except:
            logger.exception("Parsing error")
            raise

    def deserialize(self, data):
        """ Deserialize a received message.

        :param data: The received message as a bytearray.
        :type data: bytearray

        :return: Event object if deserialization is successful, None otherwise.
        :rtype: :class:`~ttgwlib.events.event.Event`
        """
        opcode = data[1]
        if opcode in MESH_EVENT_OPCODES:
            return MESH_EVENT_OPCODES[opcode](data[2:], self.gw)
        if opcode == 0xD0 or opcode == 0xD1:
            return self.model_deserialize(data[2:])
        return None

    def model_deserialize(self, data):
        """ Deserialize a model-specific message.

        :param data: The received model message as a bytearray.
        :type data: bytearray

        :return: Event object if deserialization is successful, None otherwise.
        :rtype: :class:`~ttgwlib.events.event.Event`
        """
        data_unpacked = struct.unpack("<HHHHBB6sbHI", data[0:23])
        mesh_data = {}
        mesh_data["src"] = data_unpacked[0]
        mesh_data["dst"] = data_unpacked[1]
        mesh_data["appkey_handle"] = data_unpacked[2]
        mesh_data["subnet_handle"] = data_unpacked[3]
        mesh_data["ttl"] = data_unpacked[4]
        mesh_data["adv_addr_type"] = data_unpacked[5]
        adv_addr = bytearray(data_unpacked[6])
        adv_addr.reverse()
        mesh_data["adv_addr"] = bytes(adv_addr)
        mesh_data["rssi"] = data_unpacked[7]
        mesh_data["actual_length"] = data_unpacked[8]
        mesh_data["sequence_number"] = data_unpacked[9]
        raw_model_data = data[23:] # Variable length

        # Check replay cache
        if (not self.gw.replay_cache.check_seq_number(mesh_data["src"],
                mesh_data["sequence_number"])):
            return None

        logger.log(9, f"{mesh_data['src']=}, {mesh_data['dst']=}, " +
                     f"{mesh_data['ttl']=}, {mesh_data['sequence_number']=}")

        # Check node exists
        # If addr <= 10, msg is from another gateway (transport model)
        #TODO Create some object or class to reference other gateways
        node = self.gw.node_db.get_node_by_address(mesh_data["src"])
        if node is None and mesh_data["src"] > 10:
            return model_events.UnknownNode(mesh_data, self.gw)

        opcode, model_data = self.model_get_opcode(raw_model_data)
        if opcode in MODEL_EVENT_OPCODES:
            return MODEL_EVENT_OPCODES[opcode](mesh_data, model_data, node,
                self.gw)
        return None

    def model_get_opcode(self, data):
        """ Extract the opcode from the model data.

        :param data: The received model data as a bytearray.
        :type data: bytearray

        :return: A tuple containing the opcode and the remaining model data.
        :rtype: class:`~ttgwlib.events.event.Event`
        """
        # Mask for opcode size in first byte: 0b00XX XXXX
        # 00/01 (1 Byte), 10 (2 Bytes), 11 (3 Bytes)
        op_format = (data[0] & 0xC0) >> 6
        if op_format == 0 or op_format == 1:
            opcode = int.from_bytes(data[0:1], "big")
            model_data = data[1:]
        elif op_format == 2:
            opcode = int.from_bytes(data[0:2], "big")
            model_data = data[2:]
        else:
            opcode = int.from_bytes(data[0:3], "big")
            model_data = data[3:]
        return opcode, model_data
