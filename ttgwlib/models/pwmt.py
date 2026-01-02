import struct
import logging

import ttgwlib.events.time_events as te
from ttgwlib.models.task import Task
from ttgwlib.models.model import Model
from ttgwlib.models.task_gw import TaskOpcode
from ttgwlib.events.event import EventType

def status_str(status):
    if status == 0:
        return "SUCCESS"
    error_list = []
    if status & (1 << 0):
        error_list.append("GENERAL_ERR")
    if status & (1 << 1):
        error_list.append("OVERFLOW_ERR")
    if status & (1 << 2):
        error_list.append("CALC_ERR")
    if status & (1 << 3):
        error_list.append("MEASURE_ERR")
    if status & (1 << 4):
        error_list.append("TIMEOUT_ERR")
    return "/".join(error_list)

class Pwmt(Model):
    MODEL_ID = 0x001C
    VENDOR_ID = MODEL_ID

    CONF = Model.opcode_to_bytes(0xC0, VENDOR_ID)

    def __init__(self, gateway):
        self.gw = gateway
        self.logger = logging.getLogger(__name__)
        handlers = [
            self.pwmt_handler,
        ]
        super().__init__(gateway, handlers)

    def conf(self, node, clamps_conf):
        self.logger.debug(clamps_conf)
        msg = bytearray()
        msg += self.CONF
        msg += struct.pack("<BB", clamps_conf["metric_type"], clamps_conf["values"])
        self.send(msg, node)

    def pwmt_handler(self, event):
        self.logger.debug("Event type: %d", event.event_type)
        if event.event_type == EventType.PWMT_STATUS:
            status = event.data["status"]
            if status != 0:
                self.logger.error("PWMT error %s", status_str(status))
            n_msgs = event.data["n_msgs"]
            n_clamps = event.data["n_clamps"]
            self.logger.debug("PWMT status: %s, clamps number: %d, messages to send: %d",
                    status_str(status), n_clamps, n_msgs)
        if event.event_type in (EventType.PWMT_VOLTAGES,
                EventType.PWMT_FREQUENCIES, EventType.PWMT_VI,
                EventType.PWMT_P, EventType.PWMT_Q, EventType.PWMT_S,
                EventType.PWMT_PF, EventType.PWMT_E, EventType.PWMT_E_RET):
            status = event.data["status"]
            if status != 0:
                self.logger.error("PWMT error %s", status_str(status))
            value_type = ""
            if event.data["value_type"] == 0:
                value_type += "avg"
            elif event.data["value_type"] == 1:
                value_type += "max"
            elif event.data["value_type"] == 2:
                value_type += "min"
            else:
                value_type = f'UNK({event.data["value_type"]})'
        if event.event_type in (EventType.PWMT_VOLTAGES,
                EventType.PWMT_FREQUENCIES):
            vid = event.data["vid"]
            if event.event_type == EventType.PWMT_VOLTAGES:
                v1 = event.data["v1"]
                v2 = event.data["v2"]
                v3 = event.data["v3"]
                self.logger.debug("PWMT voltages (status: %s, type: %s, VID: %d): %.2fV, %.2fV, %.2fV",
                    status_str(status), value_type, vid, v1, v2, v3)
            elif event.event_type == EventType.PWMT_FREQUENCIES:
                f1 = event.data["f1"]
                f2 = event.data["f2"]
                f3 = event.data["f3"]
                self.logger.debug("PWMT frequencies (status: %s, type: %s, VID: %d): %.2fHz, %.2fHz, %.2fHz",
                    status_str(status), value_type, vid, f1, f2, f3)
        if event.event_type in (EventType.PWMT_VI, EventType.PWMT_P,
                EventType.PWMT_Q, EventType.PWMT_S, EventType.PWMT_PF,
                EventType.PWMT_E, EventType.PWMT_E_RET):
            ch_id = event.data["ch_id"]
            if ch_id == 0xFF:
                ch_id = "TOTAL"
            else:
                ch_id = str(ch_id)
            vid = event.data["vid"]
            if event.event_type == EventType.PWMT_VI:
                v = event.data["v"]
                i = event.data["i"]
                self.logger.debug("PWMT CH %s VI (status: %s, type: %s, VID: %d): %.2fV, %.2fA",
                    ch_id, status_str(status), value_type, vid, v, i)
            elif event.event_type == EventType.PWMT_P:
                p = event.data["p"]
                self.logger.debug("PWMT CH %s P (status: %s, type: %s, VID: %d): %.2fW",
                    ch_id, status_str(status), value_type, vid, p)
            elif event.event_type == EventType.PWMT_Q:
                q = event.data["q"]
                self.logger.debug("PWMT CH %s Q (status: %s, type: %s, VID: %d): %.2fVAr",
                    ch_id, status_str(status), value_type, vid, q)
            elif event.event_type == EventType.PWMT_S:
                s = event.data["s"]
                self.logger.debug("PWMT CH %s S (status: %s, type: %s, VID: %d): %.2fVA",
                    ch_id, status_str(status), value_type, vid, s)
            elif event.event_type == EventType.PWMT_PF:
                pf = event.data["pf"]
                self.logger.debug("PWMT CH %s pf (status: %s, type: %s, VID: %d): %.2f",
                    ch_id, status_str(status), value_type, vid, pf)
            elif event.event_type == EventType.PWMT_E:
                e = event.data["e"]
                self.logger.debug("PWMT CH %s E (status: %s, type: %s, VID: %d): %dWh",
                    ch_id, status_str(status), value_type, vid, e)
            elif event.event_type == EventType.PWMT_E_RET:
                e_ret = event.data["e_ret"]
                self.logger.debug("PWMT CH %s Eret (status: %s, type: %s, VID: %d): %dWh",
                    ch_id, status_str(status), value_type, vid, e_ret)

    def set_pwmt_rate(self, node, rate):
        self.gw.models.task_gw.set_rate(node, TaskOpcode.TASK_OP_PWMT_READ,
            rate)

    def set_pwmt_rate_legacy(self, node, rate):
        self.gw.models.task_gw.set_rate_legacy(node,
            TaskOpcode.TASK_OP_PWMT_READ, rate)

    def set_pwmt_conf(self, node, clamps_conf):
        self.add_task(ConfigPwmtTask(node, self, clamps_conf))

class ConfigPwmtTask(Task):
    def __init__(self, node, model, clamps_conf):
        super().__init__(node, [EventType.PWMT_CONF_ACK],
                [EventType.TASK_TIMEOUT])
        self.model = model
        self.clamps_conf = clamps_conf
        self.model.logger.info("Scheduled setting pwmt config for node %s",
            node.mac.hex())
        self.retries = 0
        self.timeout = None

    def execute(self):
        self.model.conf(self.node, self.clamps_conf)
        self.timeout = te.TaskTimeout(self.node, 2.5, self.model.gw)
        self.retries += 1

    def success(self, event):
        self.timeout.cancel()
        self.model.logger.info("Power meter config of node %s "
            + "changed successfully", event.node.mac.hex())

    def error(self, event):
        if self.retries < self.MAX_RETRIES:
            self.execute()
        else:
            self.model.logger.info("Max retries for %s, node %s", str(self),
                self.node.mac.hex())
            self.model.reschedule_tasks(self.node)
