import logging
import time

import ttgwlib.events.mesh_events as events
from ttgwlib import commands
from ttgwlib.platform.exception import GatewayError



logger = logging.getLogger(__name__)


class HwSelfTest:
    """ Class to perform a hardware self-test on a gateway device.

    The self-test will send a software reset command to the micro-controller and
    an echo command, checking for appropriate responses within a timeout period.
    """
    SELF_TEST_TIMEOUT = 10
    ECHO_PAYLOAD = "0204FF"
    def __init__(self, gateway):
        """ Initialize the hardware self-test with the specified gateway.

        :param gateway: The gateway device to be tested.
        :type gateway: :class:`~ttgwlib.gateway.Gateway`
        """
        self.gw = gateway
        self.reset_flag = False
        self.echo_flag = False

    def reset_handler(self, event):
        """ Event handler for device reset events.

        :param event: The event object containing event details.
        :type event: :class:`~ttgwlib.events.event.Event`
        """
        if event.event_type == events.EventType.DEV_RESET:
            self.gw.remove_event_handler(self.reset_handler)
            self.reset_flag = True
            self.send_echo()

    def echo_handler(self, event):
        """ Event handler for device echo events.

        :param event: The event object containing event details.
        :type event: :class:`~ttgwlib.events.event.Event`
        """
        if event.event_type == events.EventType.ECHO:
            self.gw.remove_event_handler(self.echo_handler)
            if event.data["echo"] == bytes.fromhex(self.ECHO_PAYLOAD):
                self.echo_flag = True

    def reset_device(self):
        """ Send a reset command to the gateway device.
        """
        msg = commands.Reset()
        self.gw.uart.send_msg(msg.serialize())

    def send_echo(self):
        """ Send an echo command to the gateway device.
        """
        self.echo_flag = False
        msg = commands.Echo(bytes.fromhex(self.ECHO_PAYLOAD))
        self.gw.uart.send_msg(msg.serialize())

    def run(self):
        """ Execute the hardware self-test.

        :raises GatewayError: If the self-test fails due to a timeout.
        """
        logger.info("Performing hardware self test")
        self.reset_flag = False
        self.echo_flag = False
        self.gw.add_event_handler(self.reset_handler)
        self.gw.add_event_handler(self.echo_handler)
        self.reset_device()
        start_time = time.time()
        while time.time() - start_time < self.SELF_TEST_TIMEOUT:
            if self.reset_flag and self.echo_flag:
                break
            time.sleep(0.1)
        if not self.reset_flag or not self.echo_flag:
            raise GatewayError("Hardware self test timeout")
        logger.info("Hardware self test successful")
