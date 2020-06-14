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

        self.mqttc = paho.mqtt.client.Client()
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

    def _mqtt_on_connect(self, client, userdata, flags, rc):
        logging.info('Connected to MQTT broker with code %s', rc)

        lut = {paho.mqtt.client.CONNACK_REFUSED_PROTOCOL_VERSION: 'incorrect protocol version',
               paho.mqtt.client.CONNACK_REFUSED_IDENTIFIER_REJECTED: 'invalid client identifier',
               paho.mqtt.client.CONNACK_REFUSED_SERVER_UNAVAILABLE: 'server unavailable',
               paho.mqtt.client.CONNACK_REFUSED_BAD_USERNAME_PASSWORD: 'bad username or password',
               paho.mqtt.client.CONNACK_REFUSED_NOT_AUTHORIZED: 'not authorised'}

        if rc != paho.mqtt.client.CONNACK_ACCEPTED:
            logging.error('Connection refused from reason: %s', lut.get(rc, 'unknown code'))

        if rc == paho.mqtt.client.CONNACK_ACCEPTED:
            pass

    def _mqtt_on_disconnect(self, client, userdata, rc):
        logging.info('Disconnect from MQTT broker with code %s', rc)

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
