import ssl
import asyncio
import logging
import socket
import time
import threading

from ttgwlib import Gateway, Config, TaskOpcode

import json_database


logging.basicConfig(format='%(levelname)s: %(message)s',
    filename='logfile', level=9)
# Disable aws loggings
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


DATETIME_PERIOD  = 86400
BATTERY_PERIOD   = 86400
TELEMETRY_PERIOD = 15
IAQ_PERIOD       = 60
CO2_PERIOD       = 300 # Hardcoded in FW
PWMT_PERIOD      = 300


PORT = 31888

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


class GatewayManager:
    def __init__(self, tls=True):
        self.id_count = 0
        self.active = 0
        self.tls = tls

    def run_gateway(self, socket, id):
        logger.info(f"Conection {id} from {socket.getpeername()}")
        try:
            gt = None

            def tasks_configuration_cb(node):
                gt.set_datetime(node)
                gt.config_task(node, TaskOpcode.TASK_OP_REQ_DATETIME,
                    DATETIME_PERIOD)
                gt.config_task(node, TaskOpcode.TASK_OP_NRFTEMP,
                    TELEMETRY_PERIOD)

                if node.is_low_power():
                    gt.config_task(node, TaskOpcode.TASK_OP_BAT,
                        BATTERY_PERIOD)

                if node.has_co2():
                    gt.config_task(node,
                        TaskOpcode.TASK_OP_NRFTEMP_START_CO2, 0)
                    gt.config_task(node, TaskOpcode.TASK_OP_NRFTEMP_CO2,
                        CO2_PERIOD)

                if node.is_power_meter():
                    gt.config_task(node, TaskOpcode.TASK_OP_PWMT_START, 0)
                    gt.config_task(node, TaskOpcode.TASK_OP_PWMT_READ,
                            PWMT_PERIOD)

            config_db = json_database.JsonDatabase("database.json")
            config = Config(config_db, "cloud", port=socket,
                    config_cb=tasks_configuration_cb)
            gt = Gateway()
            gt.init(config)
            #gt.start_scan(["DA51"])
            gt.start_scan(["DA51", "0639"])

            while True:
                time.sleep(60)
                conn = gt.check_connection()
                logger.debug(f"Gateway {id}: {conn}")
                if not conn:
                    gt.stop()
                    logger.info(f"Close connection {id}")
                    self.active -= 1
                    return
        except:
            logger.exception("run_gateway exception")
            raise

    async def server_cb(self, reader, writer):
        socket = writer.get_extra_info("socket").dup()
        socket.setblocking(True)
        writer.close()
        await writer.wait_closed()

        if self.tls:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.options |= ssl.OP_NO_SSLv2
            ssl_context.options |= ssl.OP_NO_SSLv3
            ssl_context.options |= ssl.OP_NO_TLSv1
            ssl_context.options |= ssl.OP_NO_TLSv1_1
            ssl_context.options |= ssl.OP_SINGLE_DH_USE
            ssl_context.options |= ssl.OP_SINGLE_ECDH_USE
            ssl_context.load_cert_chain("certs/server.crt", "certs/server.key")
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            ssl_context.load_verify_locations("certs/ca.crt")
            socket = ssl_context.wrap_socket(socket, server_side=True)

        self.id_count += 1
        self.active += 1
        threading.Thread(target=self.run_gateway,
                name=f"gateway_{self.id_count}",
                args=(socket, self.id_count)).start()


async def server():
    gw_manager = GatewayManager()
    server = await asyncio.start_server(gw_manager.server_cb, get_ip(), PORT)

    addr = server.sockets[0].getsockname()
    logger.info(f"Serving on {addr}")

    while True:
        await asyncio.sleep(30)
        logger.debug(f"Active gateways: {gw_manager.active} " +
            f"({threading.active_count()} threads)")


if __name__ == "__main__":
    logger.info("Starting  TCP server...")
    asyncio.run(server())