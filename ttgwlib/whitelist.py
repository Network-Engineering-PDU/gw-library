from ttgwlib.node import Node

class Whitelist:
    """ Whitelist is responsible for managing the whitelist of nodes for a given
    gateway.

    This module does not implement any restrictions or privileges for the nodes
    belonging to the whitelist; it only implements an interface to add, remove,
    and get the nodes from the list.
    """

    def __init__(self, gateway):
        """ Constructor for Whitelist.

        :param gateway: The gateway instance associated with this whitelist.
        :type gateway: :class:`~ttgwlib.gateway.Gateway`
        """
        self.gw = gateway
        self.whitelist = []

    def add_node(self, node):
        """ Add a node to the whitelist.

        :param node: The node to add to the whitelist
        :type node: :class:`~ttgwlib.node.Node`
        """
        if not isinstance(node, Node):
            return False
        if node in self.whitelist:
            return True
        self.whitelist.append(node)
        return True

    def remove_node(self, node):
        """ Remove a node from the whitelist.

        :param node: The node to remove from the whitelist
        :type node: :class:`~ttgwlib.node.Node`
        """
        if not isinstance(node, Node):
            return False
        if node not in self.whitelist:
            return False
        if self.gw.models.task_queue.node_is_in_queue(node):
            self.gw.models.task_queue.node_clean_tasks(node)
        self.whitelist.remove(node)
        return True

    def is_node_in_whitelist(self, node):
        """ Check if a node is in the whitelist.

        :param node: The node to check if it is in the whitelist
        :type node: :class:`~ttgwlib.node.Node`
        """
        if not isinstance(node, Node):
            return False
        return node in self.whitelist

    def get_nodes(self):
        """ Get the list of nodes in the whitelist.
        """
        return self.whitelist
