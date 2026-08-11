"""Home Assistant MQTT Discovery for RESOL DeltaSol telemetry."""

from __future__ import annotations

from typing import Any


class HomeAssistantDiscovery:
    """Publish retained Home Assistant configuration and DeltaSol states."""

    _SENSORS = {
        "S1": ("collector_temperature", "Collector temperature", "collector/temperature", "°C", "temperature"),
        "S2": ("boiler_bottom_temperature", "Boiler bottom temperature", "boiler-bottom/temperature", "°C", "temperature"),
        "S3": ("boiler_top_temperature", "Boiler top temperature", "boiler-top/temperature", "°C", "temperature"),
        "S4": ("return_temperature", "Return temperature", "return/temperature", "°C", "temperature"),
        "SpeedRelay1": ("relay_1_speed", "Relay 1 speed", "relay-1/speed", "%", None),
        "SpeedRelay2": ("relay_2_speed", "Relay 2 speed", "relay-2/speed", "%", None),
    }

    def __init__(
        self,
        mqtt: Any,
        *,
        topic_prefix: str,
        discovery_prefix: str = "homeassistant",
        device_name: str = "DeltaSol",
        state_topics: dict[str, str] | None = None,
    ) -> None:
        self.mqtt = mqtt
        self.topic_prefix = topic_prefix.strip("/")
        self.discovery_prefix = discovery_prefix.strip("/")
        self.device_name = device_name
        self.node_id = "solar_deltasol"
        self.state_topics = state_topics or {
            key: spec[2] for key, spec in self._SENSORS.items()
        }

    def _topic(self, suffix: str) -> str:
        return f"{self.topic_prefix}/{suffix}"

    @property
    def _device(self) -> dict[str, Any]:
        return {
            "identifiers": ["solar_deltasol"],
            "name": self.device_name,
            "manufacturer": "RESOL",
            "model": "DeltaSol BS",
        }

    def _publish_discovery(self, component: str, object_id: str, payload: dict[str, Any]) -> None:
        topic = f"{self.discovery_prefix}/{component}/{self.node_id}/{object_id}/config"
        self.mqtt.publish(topic, payload, prefix=False, retain=True)

    def publish_discovery(self) -> None:
        for key, (object_id, name, default_topic, unit, device_class) in self._SENSORS.items():
            state_suffix = self.state_topics.get(key) or default_topic
            state_topic = self._topic(state_suffix)
            payload: dict[str, Any] = {
                "name": name,
                "unique_id": f"solar_deltasol_{object_id}",
                "state_topic": state_topic,
                "availability_topic": self._topic("availability"),
                "unit_of_measurement": unit,
                "state_class": "measurement",
                "device": self._device,
            }
            if device_class:
                payload["device_class"] = device_class
            self._publish_discovery("sensor", object_id, payload)

        for relay in (1, 2):
            self._publish_discovery(
                "binary_sensor",
                f"relay_{relay}",
                {
                    "name": f"Relay {relay}",
                    "unique_id": f"solar_deltasol_relay_{relay}",
                    "state_topic": self._topic(f"relay-{relay}/state"),
                    "availability_topic": self._topic("availability"),
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "device": self._device,
                },
            )

    def publish_availability(self, state: str) -> None:
        self.mqtt.publish("availability", state, use_json=False, retain=True)

    def publish_value(self, key: str, value: str) -> None:
        if key in self._SENSORS:
            self.mqtt.publish(
                self.state_topics.get(key, self._SENSORS[key][2]),
                value,
                use_json=False,
                retain=True,
            )
        if key == "Relaymask":
            mask = int(value)
            for relay in (1, 2):
                state = "ON" if mask & (1 << (relay - 1)) else "OFF"
                self.mqtt.publish(
                    f"relay-{relay}/state", state, use_json=False, retain=True
                )
