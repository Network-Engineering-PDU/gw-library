
from enum import Enum, auto
import datetime


class Event:
    """ This is the base class for any event in the net. Any event class should
    inherit from this one.

    :param evt_type: Event type.
    :type evt_type: :class: `events.event.EventType`
    :param data: Event data.
    :type data: dict
    :param gw: Reference to gateway which generated the event.
    :type data: `ttgwlib.Gateway`
    :param date: Event time.
    :type data: `datetime.datetime`
    """
    def __init__(self, event_type, data, gw, date=None):
        self.event_type = event_type
        self.data = data
        self.gw = gw
        if date:
            self.date = date
        else:
            self.date = datetime.datetime.now(datetime.timezone.utc)

class EventType(Enum):
    """ Event type list. """

    # Mesh events
    ECHO = auto()
    DEV_RESET = auto()
    UNPROV_DISC = auto()
    PROV_LINK_ESTABLISHED = auto()
    PROV_LINK_CLOSED = auto()
    PROV_CAPS = auto()
    PROV_COMPLETE = auto()
    PROV_AUTH = auto()
    PROV_ECDH = auto()
    PROV_FAILED = auto()
    MESH_TX_COMPLETE = auto()

    # Application events
    APP_EVENT = auto()
    SEQ_UPDATE = auto()
    CACHE_SIZE = auto()
    SD_ENABLED = auto()

    # Response events
    RSP_EVENT = auto()
    RSP_SEND = auto()

    # Uart events
    UART_DISCONNECTION = auto()

    # Model events
    UNKNOWN_NODE = auto()
    COMPOSITION_DATA = auto()
    APPKEY_STATUS = auto()
    MODEL_BIND = auto()
    MODEL_PUBLICATION = auto()
    NODE_RESET = auto()
    TEMP_DATA = auto()
    TEMP_DATA_RELIABLE = auto()
    IA_ACK = auto()
    TEMP_CONFIG_ACK = auto()
    TEMP_CALIB_ACK = auto()
    TEMP_CALIB_RESET_ACK = auto()
    TEMP_HEATER_NOTIFY = auto()
    IAQ_DATA = auto()
    CO2_DATA = auto()
    PWMT_CONF_ACK = auto()
    PWMT_DATA = auto()
    PWMT_STATUS = auto()
    PWMT_VOLTAGES = auto()
    PWMT_FREQUENCIES = auto()
    PWMT_VI = auto()
    PWMT_P = auto()
    PWMT_Q = auto()
    PWMT_S = auto()
    PWMT_PF = auto()
    PWMT_E = auto()
    PWMT_E_RET = auto()
    OUTPUT_ACK = auto()
    OUTPUT_CMD_ACK = auto()
    OUTPUT_CMD_NACK = auto()
    OUTPUT_CMD_ERROR = auto()
    OUTPUT_GET_RSP = auto()
    BAT_DATA = auto()
    TAP_NOTIFY = auto()
    TAP_ACK_CONF = auto()
    LIGHT_ACK = auto()
    RSSI_NEIGHBR_ACK = auto()
    RSSI_NEIGHBR_DATA = auto()
    RSSI_STATUS_ACK = auto()
    RSSI_PING = auto()
    RSSI_PING_ACK = auto()
    PING_TIMEOUT = auto()
    POWER_ACK = auto()
    HWM_DATA = auto()
    HWM_ACK = auto()
    DATETIME_REQ = auto()
    DATETIME_ACK = auto()
    TASK_ACK = auto()
    TASK_CHANGE_ACK = auto()
    TASK_DELETE_ACK = auto()
    TASK_DELETE_OP_ACK = auto()
    TASK_SEND_TASKS = auto()
    TASK_GET_TASKS_ACK = auto()
    WAKE_NOTIFY = auto()
    WAKE_RESET = auto()
    WAKE_ACK_SLEEP = auto()
    WAKE_ACK_WAIT = auto()
    WAKE_ACK_ALIVE = auto()
    OTA_VERSION_ACK = auto()
    OTA_STATUS_ACK = auto()
    OTA_STORE_ACK = auto()
    OTA_RELAY_ACK = auto()
    BEACON_START_ACK = auto()
    BEACON_STOP_ACK = auto()
    TRANSPORT_RECV = auto()
    TRANSPORT_FR_START = auto()
    TRANSPORT_FR_DATA = auto()
    TRANSPORT_FR_END = auto()
    DIAGNOSIS_UPTIME = auto()
    DIAGNOSIS_LOOPTIME = auto()
    DIAGNOSIS_RX_MSGS = auto()
    DIAGNOSIS_TX_MSGS = auto()
    DIAGNOSIS_REBOOTS = auto()
    DIAGNOSIS_WAKETIME = auto()

    # Time events
    CONFIGURATION_TIMEOUT = auto()
    SCAN_TIMEOUT = auto()
    TASK_TIMEOUT = auto()
