import queue
import logging
import threading
import socket


logger = logging.getLogger(__name__)


class UartSocket:
    uart_socket_id = 0
    def __init__(self, _socket):
        """ UartSocket is responsible for managing the UART communication over
        a socket with threading support for concurrent reading and writing.

        It implements two threads: a read thread that continuously reads data
        from the socket and puts it into the read queue; and a write thread
        that continuously retrieves data from the write queue and sends
        it through the socket. It also implements an interface to send and
        receive messages to and from the socket.

        :param _socket: The socket object for communication.
        :type _socket: socket.socket
        """
        self.socket = _socket
        self.socket.settimeout(5)
        self.read_running = threading.Event()
        self.write_running = threading.Event()
        self.connected = threading.Event()
        self.read_queue = queue.Queue()
        self.write_queue = queue.Queue()
        self.read_thd = None
        self.write_thd = None
        self.uart_socket_id = UartSocket.uart_socket_id
        UartSocket.uart_socket_id += 1

    def start(self):
        """ Start the UART socket communication.

        This method initializes and starts the reading and writing threads
        for handling socket communication.
        """
        self.read_thd = threading.Thread(target=self.read,
            name=f'Socket Reader {self.uart_socket_id}')
        self.write_thd = threading.Thread(target=self.write,
            name=f'Socket Writer {self.uart_socket_id}')
        self.read_running.set()
        self.write_running.set()
        self.connected.set()
        self.read_thd.start()
        self.write_thd.start()
        logger.debug("Uart socket start")

    def stop(self):
        """ Stop the UART socket communication.

        This method stops the reading and writing threads and closes the socket
        connection gracefully.
        """
        if not self.read_running.is_set() and not self.write_running.is_set():
            logger.warning("Uart socket already stopped")
            return

        self.read_running.clear()
        self.write_running.clear()
        self.connected.clear()
        if self.read_thd and self.read_thd.is_alive():
            self.read_thd.join(timeout=10)
        if self.write_thd and self.write_thd.is_alive():
            self.write_thd.join(timeout=10)
        if self.read_thd.is_alive() or self.write_thd.is_alive():
            logger.warning("Uart threads still alive")
        logger.debug("Uart socket stop")

    def read(self):
        """ Read loop function, executed by the thread.

        This method continuously reads data from the socket and puts it into the
        read queue. It stops if the socket is disconnected or an error occurs.
        """
        while self.read_running.is_set():
# pylint: disable=bare-except
            try:
                msg = self.socket.recv(4096)
                logger.log(9, f"Socket -> Queue: {msg}")
                if not msg:
                    logger.error("Receive error")
                    self.connected.clear()
                    break
                for b in msg:
                    self.read_queue.put(int.to_bytes(b, 1, "little"))
            except socket.timeout:
                continue
            except OSError:
                self.connected.clear()
                break
            except:
                logger.exception("Error in read thread")
# pylint: enable=bare-except
        logger.debug(f"Uart socket read {self.uart_socket_id} closed")

    def write(self):
        """ Write loop function, executed by the thread.

        This method continuously retrieves data from the write queue and sends
        it through the socket. It ensures that any remaining messages are sent
        before closing the socket.
        """
        while self.write_running.is_set():
            try:
                msg = self.write_queue.get(timeout=1)
                logger.log(9, f"Socket <- Queue: {msg}")
                sent = self.socket.send(msg)
                if sent != len(msg):
                    logger.error(f"Send error: {sent}/{len(msg)}")
            except queue.Empty:
                continue

        # When the write_thread is closed, wait for read_thread to end
        if self.read_thd and self.read_thd.is_alive():
            self.read_thd.join(timeout=10)
            if self.read_thd.is_alive():
                logger.warning("Failed to join read_thd in time")

        # Then, send any messages left
        while not self.write_queue.empty():
            msg = self.write_queue.get()
# pylint: disable=bare-except
            try:
                self.socket.send(msg)
            except:
                logger.exception("Failed to send remain data")
                break
# pylint: enable=bare-except

    def get_byte(self, timeout=None):
        """ Retrieve a byte from the read queue.

        This method retrieves a byte from the read queue, waiting up to the
        specified timeout.

        :param timeout: The maximum time (in seconds) to wait for a byte.
        :type timeout: float

        :return: The retrieved byte, or an empty byte if the timeout is reached.
        :rtype: byte
        """
        try:
            logger.log(9, "get_byte")
            return self.read_queue.get(timeout=timeout)
        except queue.Empty:
            return bytes()

    def send_msg(self, msg):
        """ Send a message through the socket.

        This method puts a message into the write queue to be sent by the
        writing thread.

        :param msg: The message to be sent.
        :type msg: bytearray
        """
        logger.log(9, f"TX: {msg.hex()}")
        self.write_queue.put(msg)

    def is_connected(self):
        """ Check if the UART socket is connected.

        :return: True if connected, False otherwise.
        :rtype: bool
        """
        return self.connected.is_set()
