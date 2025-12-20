import queue
import logging
import threading

from ttgwlib.events.event import EventType


class EventHandler:
    """ EventHandler is responsible for handling any event in the library and
    dispatching them to the registered handlers.
    """
    ev_id = 0
    def __init__(self):
        """ Initialize the event handler.

        This sets up the logging, handler list, queue, and threading for the
        event handling system.
        """
        self.logger = logging.getLogger(__name__)
        self.handler_list = []
        self.handler_list_lock = threading.RLock()
        self.event_queue = queue.Queue()
        self.ev_id = EventHandler.ev_id
        self.handler_thd = None
        EventHandler.ev_id += 1
        self.running = False

    def start(self):
        """ Start the event handler thread.

        This method starts a new thread to process the events from the queue.
        """
        if self.running:
            self.logger.warning("Event handler already running")
            return
        self.logger.debug("Event handler start")
        self.running = True
        self.handler_thd = threading.Thread(target=self.process_packets,
            name=f'EvtHandler {self.ev_id}')
        self.handler_thd.start()

    def stop(self):
        """ Stop the event handler thread.

        This method stops the event processing thread and waits for it to
        finish.
        """
        if not self.running:
            self.logger.warning("Event handler already stopped")
            return
        self.running = False
        if self.handler_thd and self.handler_thd.is_alive():
            self.handler_thd.join(timeout=10)
            if self.handler_thd.is_alive():
                self.logger.warning("Failed to join handler_thd in time")
        with self.handler_list_lock:
            self.handler_list = []
        self.logger.debug("Event handler stop")

    def process_packets(self):
        """ Process events from the event queue.

        This method runs in a loop, fetching events from the queue and
        dispatching them to the registered handlers.
        """
        while self.running:
            try:
                event = self.event_queue.get(timeout=1)
            except queue.Empty:
                continue

            if event.event_type in (EventType.WAKE_NOTIFY,
                    EventType.WAKE_RESET, EventType.TASK_TIMEOUT,
                    EventType.CONFIGURATION_TIMEOUT):
                node = event.node
                self.logger.debug(f'Event: {event.event_type.name}, '
                    + f'Node: ({node.mac.hex()}, {node.unicast_addr})')
            else:
                if (event.event_type == EventType.RSP_EVENT
                        or event.event_type == EventType.RSP_SEND
                        or event.event_type == EventType.MESH_TX_COMPLETE
                        or event.event_type == EventType.TRANSPORT_FR_DATA):
                    self.logger.log(9, f'Event: {event.event_type.name}')
                else:
                    self.logger.log(9, f'Event: {event.event_type.name}')
# pylint: disable=bare-except
            try:
                with self.handler_list_lock:
                    for handler in self.handler_list:
                        handler(event)
            except:
                self.logger.exception("Event handler error")
# pylint: enable=bare-except

    def add_event(self, event):
        """ Add an event to the queue.

        :param event: The event to be added to the queue.
        :type event: :class:`~ttgwlib.events.event.Event`
        """
        self.event_queue.put(event)

    def add_handler(self, handler):
        """ Add a handler to the handler list.

        :param handler: The handler function to be added to the list.
        :type handler: function
        """
        with self.handler_list_lock:
            if handler not in self.handler_list:
                self.handler_list.append(handler)

    def remove_handler(self, handler):
        """ Remove a handler from the handler list.

        :param handler: The handler function to be removed from the list.
        :type handler: function
        """
        with self.handler_list_lock:
            if handler in self.handler_list:
                self.handler_list.remove(handler)
