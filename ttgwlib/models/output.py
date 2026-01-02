import struct
import logging

import ttgwlib.events.time_events as te
import ttgwlib.events.model_events as me
from ttgwlib.models.task import Task
from ttgwlib.models.model import Model
from ttgwlib.events.event import EventType


class Output(Model):
    MODEL_ID = 0x001E
    VENDOR_ID = MODEL_ID

    DAC = Model.opcode_to_bytes(0xC0, VENDOR_ID)
    RELAY = Model.opcode_to_bytes(0xC1, VENDOR_ID)
    FAILSAFE = Model.opcode_to_bytes(0xC2, VENDOR_ID)
    CMD = Model.opcode_to_bytes(0xC3, VENDOR_ID)
    START = Model.opcode_to_bytes(0xC4, VENDOR_ID)
    STOP = Model.opcode_to_bytes(0xC5, VENDOR_ID)
    ENABLE = Model.opcode_to_bytes(0xC9, VENDOR_ID)
    GET = Model.opcode_to_bytes(0xCA, VENDOR_ID)

    def __init__(self, gateway):
        self.logger = logging.getLogger(__name__)
        handlers = [
            self.output_ack_handler,
            self.output_cmd_ack_handler,
        ]
        super().__init__(gateway, handlers)

    def output_ack_handler(self, event):
        if event.event_type == EventType.OUTPUT_ACK:
            self.logger.debug("ACK output received.")

    def output_cmd_ack_handler(self, event):
        if event.event_type == EventType.OUTPUT_CMD_ACK:
            self.logger.debug("ACK CMD output received.")

    def output_dac(self, node, dac_idx, dac_value, dac_en):
        msg = bytearray()
        msg += self.DAC
        msg += struct.pack("<B", dac_idx)
        msg += struct.pack("<H", int(dac_value * 1023) & 1023)
        msg += struct.pack("<B", dac_en)
        self.send(msg, node)

    def output_relay(self, node, relay_idx, relay_status):
        msg = bytearray()
        msg += self.RELAY
        msg += struct.pack("<B", relay_idx)
        msg += struct.pack("<B", relay_status & 0x01)
        self.send(msg, node)

    def output_enable(self, node, enable):
        msg = bytearray()
        msg += self.ENABLE
        msg += struct.pack("<B", enable)
        self.send(msg, node)

    def output_failsafe(self, node, relay_status, dac_values, dacs_en):
        n_relays = len(relay_status)
        n_dacs = len(dac_values)
        n_dacs_en = len(dacs_en)
        msg = bytearray()
        msg += self.FAILSAFE
        dac1 = int(dac_values[0] * 1023) & 0x3FF if n_dacs >= 1 else  0
        dac2 = int(dac_values[1] * 1023) & 0x3FF if n_dacs >= 2 else 0
        dac1_en = dacs_en[0] & 0x01 if n_dacs_en >= 1 else 0
        dac2_en = dacs_en[1] & 0x01 if n_dacs_en >= 2 else 0
        relay1 = relay_status[0] & 0x01 if n_relays >= 1 else 0
        relay2 = relay_status[1] & 0x01 if n_relays >= 2 else 0
        data = dac1 << 14 | dac2 << 4 | dac1_en << 3 | dac2_en << 2 | relay1 << 1 | relay2
        msg += data.to_bytes(3, byteorder='little')
        self.send(msg, node)

    def output_cmd(self, node, relay_status, dac_values, dt):
        # When a CMD is sent, dacX_en is ALWAYS 1
        # We must have ALWAYS relay1, relay2, dac1, dac2
        if len(relay_status) != 2:
            self.logger.warning("Not all relays have been specified")
            return
        if len(dac_values) != 2:
            self.logger.warning("Not all DACs have been specified")
            return
        msg = bytearray()
        msg += self.CMD
        dac1_en = 1
        dac2_en = 1
        dac1 = int(dac_values[0] * 1023) & 0x3FF
        dac2 = int(dac_values[1] * 1023) & 0x3FF
        relay1 = relay_status[0] & 0x01
        relay2 = relay_status[1] & 0x01
        data = dac1 << 14 | dac2 << 4 | dac1_en << 3 | dac2_en << 2 | relay1 << 1 | relay2
        msg += data.to_bytes(3, byteorder='little')
        msg += struct.pack("<I", dt)
        self.send(msg, node)

    def output_start(self, node, n_cmds):
        msg = bytearray()
        msg += self.START
        msg += struct.pack("<I", n_cmds)
        self.send(msg, node)

    def output_stop(self, node):
        msg = bytearray()
        msg += self.STOP
        self.send(msg, node)

    def output_get(self, node):
        msg = bytearray()
        msg += self.GET
        self.send(msg, node)

    def set_dac(self, node, dac_idx, dac_value, dac_en):
        self.add_task(ChangeDacOutputTask(node, self, dac_idx,
            dac_value, dac_en))

    def set_relay(self, node, relay_idx, relay_status):
        self.add_task(ChangeRelayOutputTask(node, self,
            relay_idx, relay_status))

    def set_enable_output(self, node, enable):
        self.add_task(EnableOutputTask(node, self, enable))

    def set_failsafe(self, node, relay_status, dac_values, dacs_en):
        self.add_task(FailsafeOutputTask(node, self, relay_status,
            dac_values, dacs_en))

    def send_cmd(self, node, relay_status, dac_values, dt):
        self.add_task(CmdOutputTask(node, self, relay_status,
            dac_values, dt))

    def send_start(self, node, n_cmds):
        self.add_task(StartOutputTask(node, self, n_cmds))

    def send_stop(self, node):
        self.add_task(StopOutputTask(node, self))

    def get_output(self, node):
        self.add_task(GetOutputTask(node, self))


class ChangeDacOutputTask(Task):
    def __init__(self, node, model, dac_idx, dac_value, dac_en):
        super().__init__(node, [EventType.OUTPUT_ACK], [EventType.TASK_TIMEOUT])
        self.model = model
        self.dac_idx = dac_idx
        self.dac_value = dac_value
        self.dac_en = dac_en
        dac_en_str = "ON" if self.dac_en == 1 else "OFF"
        self.model.logger.info("Scheduled setting DAC %d to %f (%s))"
            + " for node %s", dac_idx, dac_value, dac_en_str, node.mac.hex())
        self.retries = 0
        self.timeout = None

    def execute(self):
        self.model.output_dac(self.node, self.dac_idx, self.dac_value,
            self.dac_en)
        self.timeout = te.TaskTimeout(self.node, 2.5, self.model.gw)
        self.retries += 1

    def success(self, event):
        self.timeout.cancel()
        dac_en_str = "ON" if self.dac_en == 1 else "OFF"
        self.model.logger.info("DAC %d value of node %s " \
            "changed to %f (%s) successfully",
            self.dac_idx, event.node.mac.hex(), self.dac_value, dac_en_str)

    def error(self, event):
        if self.retries < self.MAX_RETRIES:
            self.execute()
        else:
            self.model.logger.info("Max retries for %s, node %s", str(self),
                event.node.mac.hex())
            self.model.reschedule_tasks(self.node)


class ChangeRelayOutputTask(Task):
    def __init__(self, node, model, relay_idx, relay_status):
        super().__init__(node, [EventType.OUTPUT_ACK], [EventType.TASK_TIMEOUT])
        self.model = model
        self.relay_idx = relay_idx
        self.relay_status = relay_status
        self.model.logger.info("Scheduled setting relay %d to %d"
            + " for node %s", relay_idx, relay_status, node.mac.hex())
        self.retries = 0
        self.timeout = None

    def execute(self):
        self.model.output_relay(self.node, self.relay_idx, self.relay_status)
        self.timeout = te.TaskTimeout(self.node, 2.5, self.model.gw)
        self.retries += 1

    def success(self, event):
        self.timeout.cancel()
        self.model.logger.info("Relay status of node %s " \
            "changed to %d successfully",
            event.node.mac.hex(), self.relay_status)

    def error(self, event):
        if self.retries < self.MAX_RETRIES:
            self.execute()
        else:
            self.model.logger.info("Max retries for %s, node %s", str(self),
                event.node.mac.hex())
            self.model.reschedule_tasks(self.node)


class EnableOutputTask(Task):
    def __init__(self, node, model, enable):
        super().__init__(node, [EventType.OUTPUT_ACK], [EventType.TASK_TIMEOUT])
        self.model = model
        self.enable = enable
        self.model.logger.info(f"Scheduled " \
            f"{'enabling' if enable else 'disabling'} gateway output layer " \
            f"for node {node.mac.hex()}")
        self.retries = 0
        self.timeout = None

    def execute(self):
        self.model.output_enable(self.node, self.enable)
        self.timeout = te.TaskTimeout(self.node, 2.5, self.model.gw)
        self.retries += 1

    def success(self, event):
        self.timeout.cancel()
        self.model.logger.info(f"Output enable of node " \
            f"{event.node.mac.hex()} changed to: " \
            f"{'ENABLE' if self.enable else 'DISABLE'} successfully")

    def error(self, event):
        if self.retries < self.MAX_RETRIES:
            self.execute()
        else:
            self.model.logger.info("Max retries for %s, node %s", str(self),
                event.node.mac.hex())
            self.model.reschedule_tasks(self.node)


class FailsafeOutputTask(Task):
    def __init__(self, node, model, relay_status, dac_values, dacs_en):
        super().__init__(node, [EventType.OUTPUT_ACK], [EventType.TASK_TIMEOUT])
        self.model = model
        self.relay_status = relay_status
        self.dac_values = dac_values
        self.dacs_en = dacs_en
        dacs_en_str = ["ON" if x == 1 else "OFF" for x in dacs_en]
        self.model.logger.info(f"Scheduled setting failsafe " \
            f"(relays: {relay_status}, dacs: {dac_values} [{dacs_en_str}]) " \
            f"for node {node.mac.hex()}")
        self.retries = 0
        self.timeout = None

    def execute(self):
        self.model.output_failsafe(self.node, self.relay_status,
            self.dac_values, self.dacs_en)
        self.timeout = te.TaskTimeout(self.node, 2.5, self.model.gw)
        self.retries += 1

    def success(self, event):
        self.timeout.cancel()
        dacs_en_str = ["ON" if x == 1 else "OFF" for x in self.dacs_en]
        self.model.logger.info(f"Failsafe of node {event.node.mac.hex()} " \
            f"changed to: relays: {self.relay_status}, " \
            f"dacs: {self.dac_values} ({dacs_en_str}), successfully")

    def error(self, event):
        if self.retries < self.MAX_RETRIES:
            self.execute()
        else:
            self.model.logger.info("Max retries for %s, node %s", str(self),
                event.node.mac.hex())
            self.model.reschedule_tasks(self.node)


class CmdOutputTask(Task):
    def __init__(self, node, model, relay_status, dac_values, dt):
        super().__init__(node,
            [EventType.OUTPUT_CMD_ACK, EventType.OUTPUT_CMD_NACK],
            [EventType.TASK_TIMEOUT])
        self.model = model
        self.relay_status = relay_status
        self.dac_values = dac_values
        self.dt = dt
        self.model.logger.info(f"Scheduled send command " \
            f"(relays: {relay_status}, dacs: {dac_values}) " \
            f"for node {node.mac.hex()}")
        self.retries = 0
        self.timeout = None

    def execute(self):
        self.model.output_cmd(self.node, self.relay_status, self.dac_values,
            self.dt)
        self.timeout = te.TaskTimeout(self.node, 2.5, self.model.gw)
        self.retries += 1

    def success(self, event):
        self.timeout.cancel()
        self.model.logger.info("Command of node %s sent successfully",
            event.node.mac.hex())

    def error(self, event):
        if self.retries < self.MAX_RETRIES:
            self.execute()
        else:
            error_event = me.OutputCmdError(self.node, self.model.gw)
            self.model.gw.event_handler.add_event(error_event)
            self.model.logger.info("Max retries for %s, node %s", str(self),
                event.node.mac.hex())
            self.model.reschedule_tasks(self.node)


class StartOutputTask(Task):
    def __init__(self, node, model, n_cmds):
        super().__init__(node,
            [EventType.OUTPUT_CMD_ACK, EventType.OUTPUT_CMD_NACK],
            [EventType.TASK_TIMEOUT])
        self.model = model
        self.n_cmds = n_cmds
        self.model.logger.info("Scheduled start (n_cmds: %d)"
            + " for node %s", n_cmds, node.mac.hex())
        self.retries = 0
        self.timeout = None

    def execute(self):
        self.model.output_start(self.node, self.n_cmds)
        self.timeout = te.TaskTimeout(self.node, 2.5, self.model.gw)
        self.retries += 1

    def success(self, event):
        self.timeout.cancel()
        self.model.logger.info("Start command of node %s sent successfully",
            event.node.mac.hex())

    def error(self, event):
        if self.retries < self.MAX_RETRIES:
            self.execute()
        else:
            error_event = me.OutputCmdError(self.node, self.model.gw)
            self.model.gw.event_handler.add_event(error_event)
            self.model.logger.info("Max retries for %s, node %s", str(self),
                self.node.mac.hex())
            self.model.reschedule_tasks(self.node)


class StopOutputTask(Task):
    def __init__(self, node, model):
        super().__init__(node,
            [EventType.OUTPUT_CMD_ACK, EventType.OUTPUT_CMD_NACK],
            [EventType.TASK_TIMEOUT])
        self.model = model
        self.model.logger.info("Scheduled stop for node %s", node.mac.hex())
        self.retries = 0
        self.timeout = None

    def execute(self):
        self.model.output_stop(self.node)
        self.timeout = te.TaskTimeout(self.node, 2.5, self.model.gw)
        self.retries += 1

    def success(self, event):
        self.timeout.cancel()
        self.model.logger.info("Stop command of node %s sent successfully",
            event.node.mac.hex())

    def error(self, event):
        if self.retries < self.MAX_RETRIES:
            self.execute()
        else:
            error_event = me.OutputCmdError(self.node, self.model.gw)
            self.model.gw.event_handler.add_event(error_event)
            self.model.logger.info("Max retries for %s, node %s", str(self),
                self.node.mac.hex())
            self.model.reschedule_tasks(self.node)

class GetOutputTask(Task):
    def __init__(self, node, model):
        super().__init__(node,
            [EventType.OUTPUT_GET_RSP], [EventType.TASK_TIMEOUT])
        self.model = model
        self.model.logger.info("Scheduled get output for node %s",
            node.mac.hex())
        self.retries = 0
        self.timeout = None

    def execute(self):
        self.model.output_get(self.node)
        self.timeout = te.TaskTimeout(self.node, 2.5, self.model.gw)
        self.retries += 1

    def success(self, event):
        self.timeout.cancel()
        self.model.logger.info(f"R1: {event.data['relay1']}, " \
            f"R2: {event.data['relay2']}, " \
            f"D1: {event.data['dac1']:.2f} ({event.data['dac1_en']}), " \
            f"D2: {event.data['dac2']:.2f} ({event.data['dac2_en']})")
        self.model.logger.info("Get output of node %s sent successfully",
            event.node.mac.hex())

    def error(self, event):
        if self.retries < self.MAX_RETRIES:
            self.execute()
        else:
            error_event = me.OutputCmdError(self.node, self.model.gw)
            self.model.gw.event_handler.add_event(error_event)
            self.model.logger.info("Max retries for %s, node %s", str(self),
                self.node.mac.hex())
            self.model.reschedule_tasks(self.node)
