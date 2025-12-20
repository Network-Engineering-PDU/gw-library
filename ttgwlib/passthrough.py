import logging
import ssl
import socket
import time
import threading
import json

from ttgwlib import commands
from ttgwlib import version


logger = logging.getLogger(__name__)


class Passthrough:
    """ Passthrough is responsible for managing the passthrough mode for a
    gateway, handling UART communication and socket connections with SSL
    support.

    A gateway in passthrough mode will redirect the entire traffic
    between the UART and the socket interfaces.
    """
    passthrough_id = 0
    def __init__(self, host, port, uart, programmer, gw_id, platform):
        """ Initializes Passthrough instance

        :param host: The remote server's address.
        :type host: str

        :param port: The remote server's TCP port.
        :type port: integer

        :param uart: The UART interface for communication.
        :type uart: :class:`~ttgwlib.uart.Uart`

        :param programmer: The programmer instance for resetting the device.
        :type programmer: :class:`~ttgwlib.platform.programmer.Programmer`

        :param gw_id: The gateway ID.
        :type gw_id: str

        :param platform: The platform type.
        :type platform: :class:`~ttgwlib.platform.board.Platform`
        """
        self.host = host
        self.port = port
        self.uart = uart
        self.gw_id = gw_id
        self.platform = platform
        self.programmer = programmer
        self.socket = None
        self.connected = threading.Event()
        self.ssl_context = None
        self.rx_thd = None
        self.tx_thd = None
        self.passthrough_id = Passthrough.passthrough_id
        Passthrough.passthrough_id += 1
        self.socket_thd = threading.Thread(target=self.keep_connected,
            name=f"Passthrough Connection {self.passthrough_id}")
        self.start_event = threading.Event()
        self.running = threading.Event()
        self.timeout = 10

    def create_default_ssl_context(self):
        """ Create a default SSL context for secure socket connections.

        This method initializes an SSL context with specific options and
        settings to ensure secure communication.
        """
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.ssl_context.options |= ssl.OP_NO_SSLv2
        self.ssl_context.options |= ssl.OP_NO_SSLv3
        self.ssl_context.options |= ssl.OP_NO_TLSv1
        self.ssl_context.options |= ssl.OP_NO_TLSv1_1
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def set_ca_cert(self, ca_cert):
        """ Set the CA certificate for SSL context verification.

        :param ca_cert: The path to the CA certificate file.
        :type ca_cert: str
        """
        if self.ssl_context is None:
            self.create_default_ssl_context()
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED
        self.ssl_context.load_verify_locations(ca_cert)

    def set_client_auth(self, client_cert, client_key):
        """ Set the client certificate and key for SSL context.

        :param client_cert: The path to the client certificate file.
        :type client_cert: str
        :param client_key: The path to the client key file.
        :type client_key: str
        """
        if self.ssl_context is None:
            self.create_default_ssl_context()
        self.ssl_context.load_cert_chain(client_cert, client_key)

    def relay_rx(self):
        """ Relay data received from UART to the socket.

        This method continuously reads data from the UART interface and sends
        it to the connected socket until the connection is closed or an error
        occurs.
        """
# pylint: disable=bare-except
        try:
            while self.running.is_set() and self.connected.is_set():
                msg = bytearray()
                while len(msg) < 255:
                    b = self.uart.get_byte(0.01)
                    if b:
                        msg += b
                    else:
                        break
                if msg:
                    try:
                        self.socket.sendall(msg)
                        logger.log(9, f"Uart -> Socket: {msg}")
                    except socket.error:
                        self.connected.clear()
                        break
        except:
            logger.exception("Error in relay_tx")
# pylint: enable=bare-except

    def relay_tx(self):
        """ Relay data received from the socket to UART.

        This method continuously reads data from the socket and sends it to the
        UART interface until the connection is closed or an error occurs.
        """
        while self.running.is_set() and self.connected.is_set():
            try:
                msg = self.socket.recv(4096)
                if not msg:
                    self.connected.clear()
                    break
                self.uart.send_msg(msg)
                logger.log(9, f"Socket <- Uart: {msg}")
            except socket.timeout:
                continue
            except socket.error:
                self.connected.clear()
                break

    def send_handshake(self):
        """ Send a handshake message to the server and wait for a response.

        This method sends a handshake message containing gateway data to the
        server and waits for a response to confirm successful connection.

        :return: True if the handshake is successful, False otherwise.
        :rtype: bool
        """
        #TODO create json with gw-data (data comming from gw-app in config)
        data = {
                "id": self.gw_id,
                "version": version.VERSION,
                "type": self.platform,
                }
        msg = json.dumps(data)
        sent = self.socket.send(msg.encode("utf-8"))
        logger.log(9, f"Data sent: {sent}, {msg}")

        if sent != len(msg):
            return False

        #TODO multiple recv loops until timeout or json correct
        try:
            msg = self.socket.recv(4096)
            if not msg:
                return False
            rx_data = json.loads(msg)
            if not "status" in rx_data:
                return False
            if rx_data["status"] == "success":
                return True
        except socket.timeout:
            logger.warning("Handshake socket timeout")
        except ValueError:
            logger.warning("Msg received is not a valid JSON")

        return False

    def keep_connected(self):
        """ Maintain the socket connection to the server.

        This method attempts to establish and maintain a socket connection to
        the server, handling reconnections and managing data relay threads for
        UART communication.
        """
        # TODO: refactor (too many statements)
        while self.running.is_set():
# pylint: disable=bare-except
            try:
                self.rx_thd = threading.Thread(target=self.relay_rx,
                    name=f"Passthrough RX {self.passthrough_id}")
                self.tx_thd = threading.Thread(target=self.relay_tx,
                    name=f"Passthrough TX {self.passthrough_id}")
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5)
                if self.ssl_context:
                    self.socket = self.ssl_context.wrap_socket(self.socket)
                logger.debug(f"Trying to connect to {self.host}:{self.port}")
                self.socket.connect((self.host, self.port))
                logger.debug("Connected")
                hs_status = self.send_handshake()
                if not hs_status:
                    raise ConnectionError("Handshake failed")
                logger.debug(f"Handshake: {hs_status}")
                self.connected.set()
            except socket.error:
                logger.debug("Unable to connect. " + \
                    f"Retrying in {self.timeout} sec")
                if self.socket:
                    self.socket.close()
                if self.running.is_set():
                    time.sleep(self.timeout)
                continue
            except:
                logger.exception("Error in keep_connected")
                if self.socket:
                    self.socket.close()
                continue
            finally:
                self.start_event.set()
# pylint: enable=bare-except
            self.uart.clean()
            self.rx_thd.start()
            self.tx_thd.start()
            if self.programmer:
                self.programmer.hard_reset()
            else:
                msg = commands.Reset()
                self.uart.send_msg(msg.serialize())
            while self.running.is_set() and self.connected.is_set():
                time.sleep(1)
            logger.debug("Connection closed")
            if self.rx_thd and self.rx_thd.is_alive():
                self.rx_thd.join(timeout=10)
                if self.rx_thd.is_alive():
                    logger.warning("Failed to join rx_thread in time")
            if self.tx_thd and self.tx_thd.is_alive():
                self.tx_thd.join(timeout=10)
                if self.tx_thd.is_alive():
                    logger.warning("Failed to join tx_thread in time")
            if self.socket:
                self.socket.close()

    def stop(self):
        """ Stop the passthrough mode and clean up resources.

        This method stops the passthrough mode, closes the socket connection,
        and joins all running threads to ensure a clean shutdown.
        """
        logger.debug(f"Stopping passthrough mode {self.passthrough_id}")
        self.running.clear()
        if self.socket:
            self.socket.close()
        if self.rx_thd and self.rx_thd.is_alive():
            self.rx_thd.join(timeout=10)
            if self.rx_thd.is_alive():
                logger.warning("Failed to join rx_thread in time")
        if self.tx_thd and self.tx_thd.is_alive():
            self.tx_thd.join(timeout=10)
            if self.tx_thd.is_alive():
                logger.warning("Failed to join tx_thread in time")
        if self.socket_thd and self.socket_thd.is_alive():
            self.socket_thd.join(timeout=15)
            if self.socket_thd.is_alive():
                logger.warning("Failed to join socket_thd in time")
        if self.uart:
            self.uart.stop()
        logger.debug(f"Passthrough stopped {self.passthrough_id}")

    def start(self):
        """ Start the passthrough mode and establish a connection.

        This method starts the passthrough mode by initiating the socket
        connection and starting the data relay threads for UART communication.
        """
        logger.debug(f"Starting passthrough mode {self.passthrough_id}")
        self.running.set()
        self.start_event.clear()
        self.socket_thd.start()
        self.start_event.wait()

    def is_running(self):
        if self.rx_thd and self.rx_thd.is_alive():
            return True

        if self.tx_thd and self.tx_thd.is_alive():
            return True

        if self.socket_thd and self.socket_thd.is_alive():
            return True

        return False


    def is_connected(self):
        """
        Check if the passthrough mode is connected.

        :return: True if connected, False otherwise.
        :rtype: bool
        """
        logger.debug(f"Passthrough is connected: {self.connected.is_set()}")
        return self.connected.is_set()
