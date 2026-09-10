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

    @patch("solarDeltaSolMQTT.vbus.serial.Serial")
    @patch("solarDeltaSolMQTT.vbus.time.time", return_value=11)
    def test_loop_drops_invalid_packet_without_publishing_fields(self, _time, serial_class):
        packet = bytearray(bytes.fromhex(
            "aa10002142100001077413023a02012d28012e0100271e640300007a650303000"
            "113491c0a26056532015803007151006400004a"
        ))
        packet[20] ^= 1
        connection = MagicMock()
        connection.read.side_effect = [
            b"\xaa", bytes(packet[1:6]), bytes(packet[6:10]), bytes(packet[10:]), b""
        ]
        serial_class.return_value = connection
        controller = DeltaSol_BS_Plus(
            "/dev/null", temperature_avg_samples=1, communication_timeout_seconds=10
        )
        controller.lastPacket = 0
        changes = []
        controller.on_change = lambda key, value: changes.append((key, value))

        with self.assertRaisesRegex(Exception, "Broken communication"):
            controller.loop_forever()

        self.assertEqual(changes, [])
        self.assertIsNone(controller.S1)
        self.assertIsNone(controller.SpeedRelay2)


    @patch("solarDeltaSolMQTT.vbus.serial.Serial")
    def test_loop_restarts_after_three_consecutive_bad_packet_crcs(self, serial_class):
        packet = bytearray(bytes.fromhex(
            "aa10002142100001077413023a02012d28012e0100271e640300007a650303000"
            "113491c0a26056532015803007151006400004a"
        ))
        packet[20] ^= 1
        connection = MagicMock()
        connection.read.side_effect = sum((
            [b"\xaa", bytes(packet[1:6]), bytes(packet[6:10]), bytes(packet[10:])]
            for _ in range(3)
        ), [])
        serial_class.return_value = connection
        controller = DeltaSol_BS_Plus("/dev/null", temperature_avg_samples=1)

        with self.assertLogs(level="WARNING") as logs:
            with self.assertRaisesRegex(Exception, "3 consecutive invalid VBus packets"):
                controller.loop_forever()

        self.assertIn("consecutive failures: 1/3", logs.output[0])
        self.assertIn("consecutive failures: 3/3", logs.output[2])
        self.assertEqual(controller.invalid_packet_count, 3)
