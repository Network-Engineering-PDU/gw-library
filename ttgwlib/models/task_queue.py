import threading
import logging

import ttgwlib.events.time_events as te
from ttgwlib.events.event import EventType
from ttgwlib.models.task import Task
from ttgwlib.models.config_client import ResetTask
from ttgwlib.models.wake_up import SleepTask, WakeTask, AliveTask


logger = logging.getLogger(__name__)

class TaskQueue:
    """ TaskQueue is responsible for managing a queue of tasks associated with
    the nodes managed by the gateway.

    It provides mechanisms for adding, cancelling, and rescheduling tasks while
    handling node configuration and sleep/wake cycles.
    """
    CONFIG_TIMEOUT = 120 # 2 minutes
    MAX_CONFIG_NODES = 10 # Best experimental result

    def __init__(self, gateway):
        """ Initialize the TaskQueue with a reference to the gateway.

        :param gateway: The gateway instance associated with this task queue.
        :type gateway: :class:`~ttgwlib.gateway.Gateway`
        """
        self.gw = gateway
        self.queue_lock = threading.RLock()
        self.queue = {} # Dict[node, List[Task]]
        self.gw.add_event_handler(self.task_handler)
        self.gw.add_event_handler(self.config_timeout_handler)
        self.config_nodes = {} # Dict[node, timer] nodes to be configured
        self.configuring_nodes = set() # nodes being configured
        self.configuration_cb = lambda node: None

    def set_configuration_cb(self, conf_cb):
        """ Set the callback function to be invoked when a node is configured.

        :param conf_cb: Callback that accepts a :class:`~ttgwlib.node.Node` as
            argument.
        :type conf_cb: function
        """
        self.configuration_cb = conf_cb

    def add_task(self, task):
        """ Add a task to the queue for the specified node.

        If the node is in the configuration process or is low power,
        a WakeTask is added before the specified task.

        :param task: The task to be added to the queue.
        :type task: :class:`~ttgwlib.models.task.Task`

        :raises TypeError: If the provided task is not an instance of Task.
        """
        if self.gw.is_listener() or self.gw.is_provisioner_mode():
            return
        if not isinstance(task, Task):
            raise TypeError(f"Invalid task type {type(task)}")
        with self.queue_lock:
            if task.node in self.config_nodes or task.node.is_low_power():
                if task.node not in self.queue:
                    wake_task = WakeTask(task.node, self.gw.models.wake_up)
                    self.queue[task.node] = [wake_task]
                self.queue[task.node].append(task)
            else:
                if task.node not in self.queue:
                    self.queue[task.node] = [task]
                    self.queue[task.node][0].execute()
                else:
                    self.queue[task.node].append(task)

    def cancel_tasks(self, node):
        """ Cancel all tasks associated with the specified node.

        :param node: The node whose tasks should be cancelled.
        :type node: :class:`~ttgwlib.node.Node`
        """
        with self.queue_lock:
            if node in self.queue:
                del self.queue[node]

    def reschedule_tasks(self, node):
        """ Reschedule tasks for the specified node.

        If the node is low power, it ensures a WakeTask is added to the queue.
        Otherwise, all tasks for that node are cancelled.

        :param node: The node for which tasks should be rescheduled.
        :type node: :class:`~ttgwlib.node.Node`
        """
        if self.gw.is_listener() or self.gw.is_provisioner_mode():
            self.cancel_tasks(node)
            return
        with self.queue_lock:
            if node.is_low_power():
                if (node in self.queue
                        and not isinstance(self.queue[node][0], WakeTask)):
                    wake_task = WakeTask(node, self.gw.models.wake_up)
                    self.queue[node].insert(0, wake_task)
            else:
                self.cancel_tasks(node)

    def get_tasks(self, node):
        """ Retrieve a list of tasks associated with the specified node.

        Only tasks that are not of type WakeTask or SleepTask are included.

        :param node: The node for which tasks should be retrieved.
        :type node: :class:`~ttgwlib.node.Node`

        :return: A list of tasks associated with the node.
        :rtype: list of :class:`~ttgwlib.models.task.Task`
        """
        tasks = []
        with self.queue_lock:
            if node in self.queue:
                for task in self.queue[node]:
                    if not isinstance(task, (WakeTask, SleepTask)):
                        tasks.append(task)
        return tasks

    def set_sleep_time(self, node, first_time):
        """ Set the sleep time configuration for the specified node.

        The method varies based on the configuration mode of the gateway.

        :param node: The node for which the sleep time is being set.
        :type node: :class:`~ttgwlib.node.Node`

        :param first_time: A flag indicating if this is the first time setting
            the sleep time.
        :type first_time: bool
        """
        if self.gw.get_config_mode() == "legacy":
            self.gw.models.task_gw.set_sleep_time_legacy(node,
                first_time=first_time)
        else:
            self.gw.models.task_gw.set_sleep_time(node)

    def sleep_node(self, node):
        """ Initiate sleep for the specified node.

        If the node is not in low power mode, an AliveTask is added.
        Otherwise, a SleepTask is added and the sleep time is configured.

        :param node: The node to be put to sleep.
        :type node: :class:`~ttgwlib.node.Node`
        """
        if not node.is_low_power():
            alive_task = AliveTask(node, self.gw.models.wake_up)
            self.queue[node] = [alive_task]
            return
        sleep_task = SleepTask(node, self.gw.models.wake_up)
        if node.sleep_period != self.gw.models.wake_up.sleep_time:
            first_time = node in self.config_nodes
            self.set_sleep_time(node, first_time=first_time)
            self.queue[node].append(sleep_task)
        else:
            self.queue[node] = [sleep_task]

    def config_timeout_handler(self, event):
        """ Handle configuration timeout events.

        If a node configuration times out, it removes the node from the
        whitelist and deletes the node from the configuration and task queue.

        :param event: The event containing information about the configuration
            timeout.
        :type event: :class:`~ttgwlib.events.event.Event`
        """
        if event.event_type == EventType.CONFIGURATION_TIMEOUT:
            if self.gw.is_node_in_whitelist(event.node):
                self.gw.remove_node_from_whitelist(event.node)
            if event.node in self.config_nodes:
                del self.config_nodes[event.node]
                if event.node in self.configuring_nodes:
                    self.configuring_nodes.remove(event.node)
            if event.node in self.queue:
                del self.queue[event.node]

    def wake_reset_cb(self, event):
        """ Callback for wake reset events.

        Logs the reset reason and initiates configuration for the node if it is
        not already being configured.

        :param event: The wake reset event containing the node and reset reason.
        :type event: :class:`~ttgwlib.events.event.Event`
        """
        reason = event.data["reset_reason"]
        reason = self.gw.models.wake_up.get_reset_reason(reason)
        logger.info("Reset reason: %s (board %d)", reason,
            event.data["board_id"])
        if (len(self.config_nodes) < self.MAX_CONFIG_NODES
                and event.node not in self.config_nodes):
            self.config_nodes[event.node] = \
                    te.ConfigTimeout(self.CONFIG_TIMEOUT, event.node, self.gw)
        if event.node in self.config_nodes:
            self.gw.models.wake_up.wake_reset_ack(event.node)

    def notify_cb(self, event):
        """ Callback for node notification events.

        Processes configuration status and manages the task queue accordingly.

        :param event: The notification event containing configuration
            information.
        :type event: :class:`~ttgwlib.events.event.Event`
        """
        # Legacy
        if not "conf" in event.data:
            if event.node in self.config_nodes:
                self.cancel_tasks(event.node)
                event.node.sleep_period = 0
                self.configuration_cb(event.node)
                logger.debug(self.queue[event.node])
            elif event.node not in self.queue:
                self.sleep_node(event.node)
        # Node needs to be configured
        elif not event.data["conf"]:
            if (len(self.config_nodes) < self.MAX_CONFIG_NODES
                    and event.node not in self.config_nodes):
                self.config_nodes[event.node] = \
                        te.ConfigTimeout(self.CONFIG_TIMEOUT, event.node,
                            self.gw)
            if (event.node in self.config_nodes
                    and event.node not in self.configuring_nodes):
                pending_tasks = self.get_tasks(event.node)
                self.cancel_tasks(event.node)
                event.node.sleep_period = 0
                self.configuration_cb(event.node)
                for pending_task in pending_tasks:
                    self.add_task(pending_task)
                self.configuring_nodes.add(event.node)
                logger.debug(self.queue[event.node])
        # Node already configured
        elif event.data["conf"] and event.node not in self.queue:
            self.sleep_node(event.node)

    def task_handler(self, event):
        """ Handle incoming events related to task execution.

        This method manages task execution based on the event type and node
        state. It handles different types of events such as wake reset, wake
        notify, and configuration timeout, and it manages the tasks accordingly.

        :param event: The event containing information about the task to be
            handled. The event is expected to have attributes like `event_type`,
            `node`, and `data`.
        :type event: :class:`~ttgwlib.events.event.Event`
        """
        if hasattr(event, "node") and event.node is not None:
            if self.gw.is_listener() or self.gw.is_provisioner_mode():
                return
            if not self.gw.whitelist.is_node_in_whitelist(event.node):
                return
            with self.queue_lock:
                if event.event_type == EventType.WAKE_RESET:
                    self.wake_reset_cb(event)

                if event.event_type == EventType.WAKE_NOTIFY:
                    self.notify_cb(event)

                if event.node in self.config_nodes:
                    self.config_nodes[event.node].restart()

                if (event.node in self.queue
                        and self.queue[event.node][0].handler(event)):
                    task = self.queue[event.node].pop(0)
                    if isinstance(task, (AliveTask, SleepTask, ResetTask)):
                        if event.node in self.config_nodes:
                            self.config_nodes[event.node].cancel()
                            del self.config_nodes[event.node]
                            if event.node in self.configuring_nodes:
                                self.configuring_nodes.remove(event.node)
                        del self.queue[event.node]
                    elif self.queue[event.node]:
                        self.queue[event.node][0].execute()
                    else:
                        if (event.node in self.config_nodes
                                or event.node.is_low_power()):
                            self.sleep_node(event.node)
                            self.queue[event.node][0].execute()
                        else:
                            del self.queue[event.node]

    def node_is_in_queue(self, node):
        """ Check if a node has pending tasks in the queue or being configured.

        This method checks whether the specified node is present in the task
        queue, the configuration nodes, or the nodes currently being configured.

        :param node: The node to check for pending tasks.
        :type node: :class:`~ttgwlib.node.Node`

        :return: True if the node has pending tasks or is being configured,
            False otherwise.
        :rtype: bool
        """
        with self.queue_lock:
            return (node in self.queue or node in self.config_nodes or
                node in self.configuring_nodes)

    def node_clean_tasks(self, node):
        """ Cancel all tasks and configuration for a specified node.

        This method removes the node from the task queue, cancels any
        configuration timers, and removes the node from the set of configuring
        nodes.

        :param node: The node for which tasks and configuration should be
            cancelled.
        :type node: :class:`~ttgwlib.node.Node`
        """
        with self.queue_lock:
            if node in self.queue:
                del self.queue[node]
        if node in self.config_nodes:
            self.config_nodes[node].cancel()
            del self.config_nodes[node]
        if node in self.configuring_nodes:
            self.configuring_nodes.remove(node)
