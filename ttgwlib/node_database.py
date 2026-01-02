class NodeDatabase:
    """ This abstract class shows the configuration database interface.

    It should be inherited by any user implementation of the configuration
    database.
    """

    def start(self):
        """ Starts the database.
        """
        raise NotImplementedError

    def stop(self):
        """ Stops the database.
        """
        raise NotImplementedError

    def set_address(self, address):
        """ Stores the unicast address in the database. If the address is
        already set, updates it.

        :param address: Address to be stored.
        :type address: int
        """
        raise NotImplementedError

    def set_netkey(self, netkey):
        """ Stores the netwkey in the database. If the netkey is already
        set, updates it.

        :param address: Address to be stored.
        :type address: int
        """
        raise NotImplementedError

    def get_address(self):
        """ Returns the gateway mesh unicast address.

        :return: Gateway unicast address.
        :rtype: integer
        """
        raise NotImplementedError

    def get_netkey(self):
        """ Returns mesh network key.

        :return: Mesh netkey.
        :rtype: bytes[16]
        """
        raise NotImplementedError

    def get_nodes(self):
        """ Returns a list with all the stored nodes.

        :return: List of all stored nodes.
        :rtype: list of :class:`~ttgwlib.node.Node`
        """
        raise NotImplementedError

    def get_node_by_address(self, address):
        """ Returns a node with the given unicast address, or None if it does
        not exist.

        :param unicast_address: Node unicast address.
        :type unicast_address: integer

        :return: The corresponding node.
        :rtype: :class:`~ttgwlib.node.Node`
        """
        raise NotImplementedError

    def get_node_by_mac(self, mac):
        """ Returns a node with the given mac address, or None if it does not
        exist.

        :param mac: Node mac address.
        :type mac: bytes[6]

        :return: The corresponding node.
        :rtype: :class:`~ttgwlib.node.Node`
        """
        raise NotImplementedError

    def store_node(self, node):
        """ Stores a node in the database. If the node is already present,
        updates it.

        :param node: Node to be stored.
        :type node: :class:`~ttgwlib.node.Node`
        """
        raise NotImplementedError

    def remove_node(self, node):
        """ Removes a node of the database.

        :param node: Node to be removed
        :type node: :class:`~ttgwlib.node.Node`
        """
        raise NotImplementedError
