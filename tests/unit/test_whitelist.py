import unittest
from unittest.mock import MagicMock
from ttgwlib.whitelist import Whitelist
from ttgwlib.node import Node

class TestWhitelist(unittest.TestCase):
    """ Test case for Whitelist class.
    """
    def setUp(self):
        """ Init configuration for each test. Creates an instance of Whitelist
        and two nodes.
        """
        self.mock_gw = MagicMock()
        self.whitelist = Whitelist(self.mock_gw)
        self.node_1 = Node(bytes("123456123456", encoding="utf-8"))
        self.node_2 = Node(bytes("abcdefabcdef", encoding="utf-8"))

    def test_add_node(self):
        """ Test adding a node to a whitelist.
        """
        # Add a single node
        self.assertTrue(self.whitelist.add_node(self.node_1),
            "Adding a node should return true")
        self.assertIn(self.node_1, self.whitelist.get_nodes(),
            "A node added to the whitelist should be in the whitelist")

        # Try to add same node. Should return True but not add it
        self.assertTrue(self.whitelist.add_node(self.node_1),
            "Adding two identical nodes should return true")
        self.assertEqual(len(self.whitelist.get_nodes()), 1,
            "Adding two identical nodes to the whitelist should not be allowed")

        # Try to add something that is not a node
        self.assertFalse(self.whitelist.add_node("not_a_node"))

    def test_remove_node_without_tasks(self):
        """ Test removing nodes from a whitelist.
        """
        # Add a single node
        self.whitelist.add_node(self.node_1)
        
        # Remove a node that is in the whitelist that has no pending tasks
        self.mock_gw.models.task_queue.node_is_in_queue.return_value = False
        self.assertTrue(self.whitelist.remove_node(self.node_1),
            "Removing an existing node from the whitelist should return true")
        self.assertNotIn(self.node_1, self.whitelist.get_nodes(),
            "A removed node should not be in the whitelist")

        # Try to remove a node that is not in the whitelist
        self.assertFalse(self.whitelist.remove_node(self.node_2),
            "Removing a node that is not in the whitelist should return false")

        # Try to remove something that is not a node
        self.assertFalse(self.whitelist.remove_node("not_a_node"),
            "Trying to remove something that is not a node should return false")

    def test_remove_node_with_tasks(self):
        """ Test removing a node with pending tasks
        """
        self.whitelist.add_node(self.node_1)
        
        # Remove a node that ishould not be possibles in the whitelist that has pending tasks
        self.mock_gw.models.task_queue.node_is_in_queue.return_value = True

        # Check that returns True
        self.assertTrue(self.whitelist.remove_node(self.node_1),
            "A node with pending tasks should be removable from the whitelist")

        # Check that node tasks is called
        self.mock_gw.models.task_queue.node_clean_tasks.assert_called_once_with(
            self.node_1)

        # Check that node was removed
        self.assertNotIn(self.node_1, self.whitelist.get_nodes(),
            "A removed node with pending should not be in the whitelist")

    def test_is_node_in_whitelist(self):
        """ Test to verify that a node is in the whitelist.
        """
        self.whitelist.add_node(self.node_1)

        # Test that node is in whitelist
        self.assertTrue(self.whitelist.is_node_in_whitelist(self.node_1),
            "A node added to the whitelist should be in the whitelist")

        # Test that node is not in whitelist
        self.assertFalse(self.whitelist.is_node_in_whitelist(self.node_2),
            "A node not added to the whitelist should not be in the whitelist")

        # Try to check something that is not a node
        self.assertFalse(self.whitelist.is_node_in_whitelist("not_a_node"),
            "An instance different from a node should not be addable")

    def test_get_nodes(self):
        """ Test obtaining every node from whitelist. """
        # Add nodes to whitelist
        self.whitelist.add_node(self.node_1)
        self.whitelist.add_node(self.node_2)

        # Check that nodes are in the list
        nodes = self.whitelist.get_nodes()
        self.assertIn(self.node_1, nodes,
            "A node added to the whitelist should be abled to be retrieved")
        self.assertIn(self.node_2, nodes,
            "A node added to the whitelist should be abled to be retrieved")
        self.assertEqual(len(nodes), 2,
            "The length of the whitelist should be equal to the nodes added")

if __name__ == '__main__':
    unittest.main()
