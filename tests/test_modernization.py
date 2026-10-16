import io
from unittest import TestCase
from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt

from solarDeltaSolMQTT.config import load_config
from solarDeltaSolMQTT.mqtt_client import MqttClient
from solarDeltaSolMQTT.vbus import DeltaSol_BS_Plus


class TestModernization(TestCase):
    def test_default_configuration_is_not_shared_between_loads(self):
        first = load_config(io.StringIO("solar:\n  device: /dev/ttyUSB0\n"))
        first["mqtt"]["prefix"] = "changed"

        second = load_config(io.StringIO("solar:\n  device: /dev/ttyUSB1\n"))

        self.assertEqual(second["mqtt"]["prefix"], "solar")

    @patch("solarDeltaSolMQTT.mqtt_client.paho.mqtt.client.Client")
    def test_mqtt_client_selects_paho_callback_api_v2(self, client_class):
        client = MagicMock()
        client_class.return_value = client

        MqttClient(host="localhost", port=1883, prefix="solar")

        client_class.assert_called_once_with(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )

    def test_temperature_frame_value_is_scaled_once(self):
        controller = DeltaSol_BS_Plus("/dev/null", temperature_avg_samples=1)

        self.assertEqual(controller.normalize_value("S1", 100), 10.0)

    def test_decodes_captured_deltasol_bs_vbus_frame_without_serial_hardware(self):
        packet = bytes.fromhex(
            "aa10002142100001077413023a02012d28012e0100271e640300007a650303000"
            "113491c0a26056532015803007151006400004a"
        )

        values = DeltaSol_BS_Plus.decode_bs_packet(packet)

        self.assertEqual(
            values,
            {
                "S1": 65.9,
                "S2": 57.0,
                "S3": 29.6,
                "S4": 30.2,
                "SpeedRelay1": 30,
                "SpeedRelay2": 100,
                "Relaymask": 3,
                "Errormask": 0,
                "SystemTime": 997,
                "Scheme": 3,
                "OptionsMask": 0,
                "RuntimeRelay1": 7369,
                "RuntimeRelay2": 9866,
                "HeatQuantity_Wh": 306,
                "HeatQuantity_kWh": 856,
                "HeatQuantity_MWh": 81,
                "Version": 100,
            },
        )

    @patch("solarDeltaSolMQTT.vbus.serial.Serial")
    def test_loop_publishes_only_a_complete_valid_packet(self, serial_class):
        packet = bytes.fromhex(
            "aa10002142100001077413023a02012d28012e0100271e640300007a650303000"
            "113491c0a26056532015803007151006400004a"
        )
        connection = MagicMock()
        connection.read.side_effect = [
            b"\xaa", packet[1:6], packet[6:10], packet[10:], KeyboardInterrupt()
        ]
        serial_class.return_value = connection
        controller = DeltaSol_BS_Plus("/dev/null", temperature_avg_samples=1)
        changes = []
        controller.on_change = lambda key, value: changes.append((key, value))

        with self.assertRaises(KeyboardInterrupt):
            controller.loop_forever()

        self.assertEqual(controller.S1, 65.9)
        self.assertEqual(controller.SpeedRelay2, 100)
        self.assertIn(("S1", 65.9), changes)

    def test_timeout_logs_no_data_without_crashing_service(self):
        controller = DeltaSol_BS_Plus("/dev/null", communication_timeout_seconds=30)
        controller.lastPacket = 0

        with self.assertLogs(level="ERROR") as logs:
            timed_out = controller.report_communication_timeout(30_001)

        self.assertTrue(timed_out)
        self.assertIn("No valid VBus packet for 30 seconds", logs.output[0])
        self.assertEqual(controller.lastPacket, 30_001)


    def test_three_consecutive_bad_packet_crcs_do_not_crash_service(self):
        controller = DeltaSol_BS_Plus("/dev/null")

        with self.assertLogs(level="WARNING") as logs:
            for _ in range(3):
                controller.record_invalid_packet("header CRC")

        self.assertIn("failures: 3", logs.output[2])
        self.assertEqual(controller.invalid_packet_count, 3)

    def test_debug_raw_bytes_are_logged_for_invalid_packet(self):
        controller = DeltaSol_BS_Plus("/dev/null", debug_raw_bytes=True)

        with self.assertLogs(level="WARNING") as logs:
            controller.record_invalid_packet('header CRC', raw=bytes.fromhex('aa0102'))

        self.assertIn("raw=aa0102", logs.output[0])

    def test_debug_raw_bytes_can_be_enabled_in_solar_config(self):
        config = load_config(io.StringIO("solar:\n  device: /dev/null\n  debug_raw_bytes: true\n"))

        self.assertTrue(config["solar"]["debug_raw_bytes"])
