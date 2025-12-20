class Config:
    """
    :param node_db: Database where the mesh network nodes are stored.
    :type node_db: :class:`~ttgwlib.node_db.NodeDatabase`

    :param config_cb: Node configuration callback function. It only has
        one parameter, the node to be configured. Optional.
    :type config_cb: function

    :param seq_number_file: File to store sequence number. Optional,
        defaults to file .seq_number in current directory.
    :type seq_number_file: str

    :param prov_mode: Enable provision mode. Optional, defaults to false.
    :type prov_mode: bool

    :param config_mode: Configuration mode. Optional, defaults to legacy.
    :type config_mode: str
    """
    def __init__(self, node_db, config_cb=None, seq_number_file=None,
            prov_mode=False, config_mode="legacy"):
        self.node_db = node_db
        self.config_cb = config_cb
        if not seq_number_file:
            seq_number_file = ".seq_number"
        self.seq_number_file = seq_number_file
        self.prov_mode = prov_mode
        self.config_mode = config_mode


class ConfigPassthrough:
    """
    :param address: The remote server's address.
    :type address: str

    :param tcp_port: The remote server's TCP port.
    :type tcp_port: integer

    :param ca_cert: The path to the CA certificate file.
    :type ca_cert: str

    :param client_cert: The path to the client certificate file.
    :type client_cert: str

    :param client_key: The path to the client private key file.
    :type client_key: str

    :param gw_id: Unique id to identify this gateway in a multigateway context.
    :type gw_id: str
    """
    def __init__(self, address, tcp_port, ca_cert, client_cert, client_key,
            gw_id):
        self.address = address
        self.tcp_port = tcp_port
        self.ca_cert = ca_cert
        self.client_cert = client_cert
        self.client_key = client_key
        self.gw_id = gw_id
