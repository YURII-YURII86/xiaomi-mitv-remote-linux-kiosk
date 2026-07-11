import unittest

from linux_kiosk_remote.common import parse_bluetooth_info, parse_controller, parse_input_devices
from linux_kiosk_remote.keymap import build_keymap_from_codes, validate_keymap
from linux_kiosk_remote.profiles import load_profiles, validate_profile
from linux_kiosk_remote.lab import build_lab_report, parse_codes_json
from linux_kiosk_remote.common import RemoteConfig


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

    def test_validate_keymap(self):
        keymap = build_keymap_from_codes({"up": 103, "down": 108, "left": 105, "right": 106, "center": 353, "back": 158})
        result = validate_keymap(keymap)
        self.assertEqual(result["actionCount"], 6)
        self.assertEqual(result["warnings"], [])

    def test_validate_keymap_warns_missing_recommended(self):
        keymap = build_keymap_from_codes({"up": 103})
        result = validate_keymap(keymap)
        self.assertTrue(any("missing recommended" in item for item in result["warnings"]))

    def test_profiles_validate(self):
        profiles = load_profiles()
        self.assertGreaterEqual(len(profiles), 2)
        ids = {p["id"] for p in profiles}
        self.assertIn("xiaomi-mitv-remote", ids)
        self.assertIn("generic-bluetooth-hid-remote", ids)
        for profile in profiles:
            self.assertIn("status", validate_profile(profile))

    def test_lab_report_from_codes(self):
        config = RemoteConfig.from_env()
        report = build_lab_report(config, codes={"up": 103, "down": 108, "left": 105, "right": 106, "center": 353, "back": 158})
        self.assertEqual(report["schema"], "xiaomi-mitv-remote-linux-kiosk.lab-report.v1")
        self.assertIn("capturedRecommendedActions", report["checks"])
        self.assertEqual(set(report["capturedActions"]), {"up", "down", "left", "right", "center", "back"})

    def test_parse_codes_json(self):
        self.assertEqual(parse_codes_json('{"up":103}'), {"up": 103})


if __name__ == "__main__":
    unittest.main()
