import logging

from ttgwlib import Gateway, Config, Node, TaskOpcode

from examples.json_database import JsonDatabase
from examples.ota import *


# Task periods
SLEEP_PERIOD     = 60
DATETIME_PERIOD  = 180
BATTERY_PERIOD   = 47
TELEMETRY_PERIOD = 29
IAQ_PERIOD       = 50
CO2_PERIOD       = 300 # Hardcoded in FW
PWMT_PERIOD      = 60


uuid_filter = ["DA51"]
mac_filter = ["FFF569011540"]


logging.basicConfig(format='%(levelname)s: %(message)s',
    filename='logfile', level=9)
# Disable aws loggings
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.WARNING)


def tasks_configuration_cb(node):
    global gt
    gt.set_datetime(node)
    gt.config_task(node, TaskOpcode.TASK_OP_REQ_DATETIME, DATETIME_PERIOD)
    gt.config_task(node, TaskOpcode.TASK_OP_NRFTEMP, TELEMETRY_PERIOD)

    if node.is_low_power():
        gt.config_task(node, TaskOpcode.TASK_OP_BAT, BATTERY_PERIOD)

    if node.has_co2():
        gt.config_task(node, TaskOpcode.TASK_OP_NRFTEMP_START_CO2, 0)
        gt.config_task(node, TaskOpcode.TASK_OP_NRFTEMP_CO2, CO2_PERIOD)

    if node.is_power_meter():
        gt.config_task(node, TaskOpcode.TASK_OP_PWMT_START, 0)
        gt.config_task(node, TaskOpcode.TASK_OP_PWMT_READ, PWMT_PERIOD)

def get_netkey(gt):
    return gt.config_db.get_config().netkeys[0].key.hex().lower()


def add_node(gt, mac, unicast_address, devkey, uuid=None, name=""):
    if isinstance(mac, str):
        mac = bytes.fromhex(mac)
    if isinstance(devkey, str):
        devkey = bytes.fromhex(devkey)
    if uuid and isinstance(uuid):
        uuid = bytes.fromhex(uuid, str)

    node = Node(mac, uuid, unicast_address, name, devkey)
    gt.store_node(node)


node_db = JsonDatabase("database.json")
gw_config = Config(node_db, "desktop", port=None,
        config_cb=tasks_configuration_cb, prov_mode=False)
gt = Gateway()
gt.init(gw_config)
gt.set_sleep_time(SLEEP_PERIOD)
