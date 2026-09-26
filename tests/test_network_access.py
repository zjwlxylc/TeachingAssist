import os
import unittest
from unittest import mock

from app.services import network


class NetworkAccessTests(unittest.TestCase):
    def test_physical_network_is_preferred_to_virtual_address(self):
        adapters = [
            {"name": "VPN", "ip": "10.0.0.2", "virtual": True, "gateway": True},
            {"name": "Ethernet", "ip": "192.168.20.15", "virtual": False, "gateway": True},
        ]
        with mock.patch.object(network, "_windows_network_candidates", return_value=adapters, create=True), \
             mock.patch.object(network.socket, "getaddrinfo", return_value=[]), \
             mock.patch.object(network.socket, "gethostbyname_ex", return_value=("host", [], ["10.0.0.2", "192.168.20.15"])):
            candidates = network.list_network_candidates()
        self.assertEqual(candidates[0]["ip"], "192.168.20.15")
        self.assertEqual(candidates[0]["name"], "Ethernet")

    def test_stale_saved_address_and_port_do_not_override_runtime(self):
        with mock.patch.object(network, "list_network_candidates", return_value=[{"name": "Ethernet", "ip": "192.168.20.15", "selected": True}]), \
             mock.patch.object(network, "load_selected_access", return_value=("10.0.0.2", 8080)), \
             mock.patch.object(network, "check_firewall", return_value={}), \
             mock.patch.dict(os.environ, {"TEACHING_ASSIST_ACTUAL_PORT": "8081"}):
            info = network.get_access_info()
        self.assertEqual(info["access_url"], "http://192.168.20.15:8081")

    def test_automatic_address_ignores_even_current_manual_selection(self):
        candidates = [{"name": "LAN", "ip": "192.168.20.15", "selected": True}, {"name": "WiFi", "ip": "192.168.30.15", "selected": False}]
        with mock.patch.object(network, "list_network_candidates", return_value=candidates), \
             mock.patch.object(network, "load_selected_access", return_value=("192.168.30.15", 8080)), \
             mock.patch.object(network, "check_firewall", return_value={}), \
             mock.patch.dict(os.environ, {"TEACHING_ASSIST_ACTUAL_PORT": "8081"}):
            info = network.get_access_info(selected_port=8888)
        self.assertEqual(info["access_url"], "http://192.168.20.15:8081")
        self.assertEqual(info["student_url"], "http://192.168.20.15:8081/student")
        self.assertEqual(len(info["candidates"]), 1)

    def test_virtual_only_is_not_advertised_as_classroom_network(self):
        with mock.patch.object(network, "_windows_network_candidates", return_value=[{"name": "VPN", "ip": "10.0.0.2", "virtual": True, "gateway": True}]):
            candidates = network.list_network_candidates()
        self.assertEqual(candidates[0]["ip"], "127.0.0.1")
