import unittest

from linux_kiosk_remote.common import parse_bluetooth_info, parse_controller, parse_input_devices
from linux_kiosk_remote.keymap import build_keymap_from_codes


class CommonParserTests(unittest.TestCase):
    def test_parse_input_devices_by_mac_and_name(self):
        text = '''I: Bus=0005 Vendor=2717 Product=0001 Version=0001
N: Name="Xiaomi RC Consumer Control"
P: Phys=00:11:22:33:44:55
U: Uniq=aa:bb:cc:dd:ee:ff
H: Handlers=kbd event10

I: Bus=0003 Vendor=0001 Product=0001 Version=0001
N: Name="USB Keyboard"
H: Handlers=sysrq kbd event3
'''
        events = parse_input_devices(text, remote_mac="AA:BB:CC:DD:EE:FF", device_name_regex="remote")
        self.assertEqual(events, [{"path": "/dev/input/event10", "name": "Xiaomi RC Consumer Control", "uniq": "aa:bb:cc:dd:ee:ff"}])

    def test_parse_input_devices_by_name_regex_without_mac(self):
        text = '''N: Name="Android TV Remote"
H: Handlers=kbd event7 event8
'''
        events = parse_input_devices(text, device_name_regex="android.*remote")
        self.assertEqual([event["path"] for event in events], ["/dev/input/event7", "/dev/input/event8"])

    def test_parse_bluetooth_info(self):
        info = parse_bluetooth_info('''Device AA:BB:CC:DD:EE:FF Remote
Name: Xiaomi RC
Paired: yes
Trusted: no
Connected: yes
UUID: Human Interface Device Service (00001812-0000-1000-8000-00805f9b34fb)
''')
        self.assertEqual(info["name"], "Xiaomi RC")
        self.assertIs(info["paired"], True)
        self.assertIs(info["trusted"], False)
        self.assertIs(info["connected"], True)
        self.assertIs(info["hid_uuid"], True)

    def test_parse_controller(self):
        controller = parse_controller('''Controller 00:00:00:00:00:00 host
Powered: yes
Discoverable: no
Pairable: yes
Discovering: no
''')
        self.assertEqual(controller, {"powered": True, "discoverable": False, "pairable": True, "discovering": False})

    def test_build_keymap_from_codes(self):
        keymap = build_keymap_from_codes({"up": 103, "center": 353}, mac="AA:BB:CC:DD:EE:FF")
        self.assertEqual(keymap["keys"]["up"]["code_text"], "KEY_UP")
        self.assertEqual(keymap["keys"]["center"]["code_text"], "KEY_SELECT")
        self.assertNotIn("down", keymap["keys"])


if __name__ == "__main__":
    unittest.main()
