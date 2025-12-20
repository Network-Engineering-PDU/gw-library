import os
import json

from ttgwlib import NodeDatabase, Node


class JsonDatabase(NodeDatabase):
    """ Implementación de una base de datos para el gateway que usa como
    almacenamiento un archivo .json.

    Debe funcionar con rutas absolutas y relativas en Windows y en Linux.

    :param json_file: archivo de la base de datos.
    :type json_file: string
    """
    def __init__(self, database_file):
        self.database_file = database_file

        if not os.path.isfile(self.database_file):
            self.address = 1
            self.netkey = os.urandom(16)
            self.node_list = []
            default_data = {}
            default_data["address"] = self.address
            default_data["netkey"] = self.netkey.hex()
            default_data["nodes"] = self.node_list
            with open(self.database_file, "w") as f:
                json.dump(default_data, f, indent=2)
        else:
            with open(self.database_file) as f:
                data = json.load(f)
            self.address = data["address"]
            self.netkey = bytes.fromhex(data["netkey"])
            self.node_list = [Node.from_json(node) for node in data["nodes"]]

    def get_address(self):
        return self.address

    def get_netkey(self):
        return self.netkey

    def write_nodes(self):
        data = {}
        data["address"] = self.address
        data["netkey"] = self.netkey.hex()
        data["nodes"] = [node.to_json() for node in self.node_list]
        with open(self.database_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_nodes(self):
        return self.node_list

    def get_node_by_mac(self, mac):
        for n in self.node_list:
            if n.mac == mac:
                return n

    def get_node_by_address(self, address):
        for n in self.node_list:
            if n.unicast_addr == address:
                return n

    def store_node(self, node):
        if node in self.node_list:
            self.node_list[self.node_list.index(node)] = node
        else:
            self.node_list.append(node)
        self.write_nodes()

    def remove_node(self, node):
        try:
            self.node_list.remove(node)
            self.write_nodes()
        except ValueError:
            pass
