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

    def output_dac(self, node, dac_value):
        msg = bytearray()
        msg += self.DAC
        msg += struct.pack("<f", dac_value)
        self.send(msg, node)

    def output_relay(self, node, relay_status):
        msg = bytearray()
        msg += self.RELAY
        msg += struct.pack("<B", relay_status)
        self.send(msg, node)

    def output_failsafe(self, node, relay_status, dac_value):
        msg = bytearray()
        msg += self.FAILSAFE
        msg += struct.pack("<B", relay_status)
        msg += struct.pack("<H", int(dac_value * 0xFFFF))
        self.send(msg, node)

    def output_cmd(self, node, relay_status, dac_value, dt):
        msg = bytearray()
        msg += self.CMD
        msg += struct.pack("<B", relay_status)
        msg += struct.pack("<H", int(dac_value * 0xFFFF))
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

    def set_dac(self, node, dac_value):
        self.add_task(ChangeDacOutputTask(node, self, dac_value))

    def set_relay(self, node, relay_status):
        self.add_task(ChangeRelayOutputTask(node, self, relay_status))

    def set_failsafe(self, node, relay_status, dac_value):
        self.add_task(FailsafeOutputTask(node, self, relay_status, dac_value))

    def send_cmd(self, node, relay_status, dac_value, dt):
        self.add_task(CmdOutputTask(node, self, relay_status, dac_value, dt))

    def send_start(self, node, n_cmds):
        self.add_task(StartOutputTask(node, self, n_cmds))

    def send_stop(self, node):
        self.add_task(StopOutputTask(node, self))


class ChangeDacOutputTask(Task):
    def __init__(self, node, model, dac_value):
        super().__init__(node, [EventType.OUTPUT_ACK], [EventType.TASK_TIMEOUT])
        self.model = model
        self.dac_value = dac_value
        self.model.logger.info("Scheduled setting dac (dac_value: %f)"
            + " for node %s", dac_value, node.mac.hex())
        self.retries = 0
        self.timeout = None

    def execute(self):
        self.model.output_dac(self.node, self.dac_value)
        self.timeout = te.TaskTimeout(self.node, 2.5, self.model.gw)
        self.retries += 1

    def success(self, event):
        self.timeout.cancel()
        self.model.logger.info("DAC value of node %s changed successfully",
            event.node.mac.hex())

    def error(self, event):
        if self.retries < self.MAX_RETRIES:
            self.execute()
        else:
            self.model.logger.info("Max retries for %s, node %s", str(self),
                self.node.mac.hex())
            self.model.reschedule_tasks(self.node)


class ChangeRelayOutputTask(Task):
    def __init__(self, node, model, relay_status):
        super().__init__(node, [EventType.OUTPUT_ACK], [EventType.TASK_TIMEOUT])
        self.model = model
        self.relay_status = relay_status
        self.model.logger.info("Scheduled setting relay (relay_status: %d)"
            + " for node %s", relay_status, node.mac.hex())
        self.retries = 0
        self.timeout = None

    def execute(self):
        self.model.output_relay(self.node, self.relay_status)
        self.timeout = te.TaskTimeout(self.node, 2.5, self.model.gw)
        self.retries += 1

    def success(self, event):
        self.timeout.cancel()
        self.model.logger.info("Relay status of node %s changed successfully",
            event.node.mac.hex())

    def error(self, event):
        if self.retries < self.MAX_RETRIES:
            self.execute()
        else:
            self.model.logger.info("Max retries for %s, node %s", str(self),
                self.node.mac.hex())
            self.model.reschedule_tasks(self.node)


class FailsafeOutputTask(Task):
    def __init__(self, node, model, relay_status, dac_value):
        super().__init__(node, [EventType.OUTPUT_ACK], [EventType.TASK_TIMEOUT])
        self.model = model
        self.relay_status = relay_status
        self.dac_value = dac_value
        self.model.logger.info("Scheduled setting failsafe "
            + "(relay_status: %d, dac_value: %d) for node %s",
            relay_status, dac_value, node.mac.hex())
        self.retries = 0
        self.timeout = None

    def execute(self):
        self.model.output_failsafe(self.node, self.relay_status, self.dac_value)
        self.timeout = te.TaskTimeout(self.node, 2.5, self.model.gw)
        self.retries += 1

    def success(self, event):
        self.timeout.cancel()
        self.model.logger.info("Failsafe of node %s changed successfully",
            event.node.mac.hex())

    def error(self, event):
        if self.retries < self.MAX_RETRIES:
            self.execute()
        else:
            self.model.logger.info("Max retries for %s, node %s", str(self),
                self.node.mac.hex())
            self.model.reschedule_tasks(self.node)


class CmdOutputTask(Task):
    def __init__(self, node, model, relay_status, dac_value, dt):
        super().__init__(node,
            [EventType.OUTPUT_CMD_ACK, EventType.OUTPUT_CMD_NACK],
            [EventType.TASK_TIMEOUT])
        self.model = model
        self.relay_status = relay_status
        self.dac_value = dac_value
        self.dt = dt
        self.model.logger.info("Scheduled send command"
            + " (relay_status: %d, dac_value: %.2f, dt: %d)"
            + " for node %s", relay_status, dac_value, dt, node.mac.hex())
        self.retries = 0
        self.timeout = None

    def execute(self):
        self.model.output_cmd(self.node, self.relay_status, self.dac_value,
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
                self.node.mac.hex())
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
