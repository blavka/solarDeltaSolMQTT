from unittest import TestCase
from unittest.mock import MagicMock

from solarDeltaSolMQTT.home_assistant import HomeAssistantDiscovery


class HomeAssistantDiscoveryTests(TestCase):
    def setUp(self):
        self.mqtt = MagicMock()
        self.discovery = HomeAssistantDiscovery(
            self.mqtt,
            topic_prefix="solar",
            discovery_prefix="homeassistant",
            device_name="DeltaSol",
        )

    def test_publishes_retained_temperature_and_relay_discovery(self):
        self.discovery.publish_discovery()

        temperature_call = next(
            call
            for call in self.mqtt.publish.call_args_list
            if call.args[0] == "homeassistant/sensor/solar_deltasol/collector_temperature/config"
        )
        self.assertEqual(temperature_call.kwargs["prefix"], False)
        self.assertTrue(temperature_call.kwargs["retain"])
        self.assertEqual(temperature_call.args[1]["state_topic"], "solar/collector/temperature")
        self.assertEqual(temperature_call.args[1]["device_class"], "temperature")

        relay_call = next(
            call
            for call in self.mqtt.publish.call_args_list
            if call.args[0] == "homeassistant/binary_sensor/solar_deltasol/relay_1/config"
        )
        self.assertEqual(relay_call.args[1]["state_topic"], "solar/relay-1/state")
        self.assertEqual(relay_call.args[1]["payload_on"], "ON")

    def test_reuses_existing_sensor_topics_and_derives_relay_states(self):
        self.discovery.publish_value("S1", "66.3")
        self.discovery.publish_value("SpeedRelay2", "100")
        self.discovery.publish_value("Relaymask", "3")

        self.mqtt.publish.assert_any_call(
            "collector/temperature", "66.3", use_json=False, retain=True
        )
        self.mqtt.publish.assert_any_call("relay-2/speed", "100", use_json=False, retain=True)
        self.mqtt.publish.assert_any_call("relay-1/state", "ON", use_json=False, retain=True)
        self.mqtt.publish.assert_any_call("relay-2/state", "ON", use_json=False, retain=True)


if __name__ == "__main__":
    import unittest

    unittest.main()
