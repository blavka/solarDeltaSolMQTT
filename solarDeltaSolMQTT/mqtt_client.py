'''
@author: karel.blavka@gmail.com
'''
import paho.mqtt.client
from paho.mqtt.client import topic_matches_sub
import logging
import simplejson as json
import time


class MqttClient:

    def __init__(self, host, port, username=None, password=None, cafile=None, certfile=None, keyfile=None, prefix=None):
        port = int(port)

        self.mqttc = paho.mqtt.client.Client(
            callback_api_version=paho.mqtt.client.CallbackAPIVersion.VERSION2
        )
        self.mqttc.on_connect = self._mqtt_on_connect
        self.mqttc.on_message = self._mqtt_on_message
        self.mqttc.on_disconnect = self._mqtt_on_disconnect
        self.prefix = prefix.rstrip('/') + '/' if prefix else None

        self.on_message = None

        if username:
            self.mqttc.username_pw_set(username, password)

        if cafile:
            self.mqttc.tls_set(cafile, certfile, keyfile)

        logging.info('MQTT broker host: %s, port: %d, use tls: %s', host, port, bool(cafile))

        self.mqttc.connect(host, port, keepalive=10)

        self._response_condition = 0
        self._response_topic = None
        self._response = None

        self._loop_start = False

    def loop_start(self):
        if self._loop_start:
            return

        self._loop_start = True
        self.mqttc.loop_start()

    def loop_forever(self):
        self._loop_start = True
        self.mqttc.loop_forever()

    def _mqtt_on_connect(self, client, userdata, connect_flags, reason_code, properties):
        logging.info('Connected to MQTT broker with reason code %s', reason_code)

        if reason_code != 0:
            logging.error('Connection refused from reason: %s', reason_code)

    def _mqtt_on_disconnect(
            self, client, userdata, disconnect_flags, reason_code, properties):
        logging.info('Disconnect from MQTT broker with reason code %s', reason_code)

    def _mqtt_on_message(self, client, userdata, message):
        logging.debug('mqtt_on_message %s %s', message.topic, message.payload)

    def publish(self, topic, payload=None, qos=1, use_json=True):
        self.loop_start()
        if isinstance(topic, list):
            topic = '/'.join(topic)
        if self.prefix:
            topic = self.prefix + topic
        if use_json:
            payload = json.dumps(payload, use_decimal=True)
        return self.mqttc.publish(topic, payload, qos=qos)
