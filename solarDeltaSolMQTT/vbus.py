#!/usr/bin/python3
'''
Created on Apr 16, 2015
@author: karel.blavka@gmail.com
'''
import serial
import time
import struct
import logging
import paho.mqtt.client as mqtt
from .moving_average import Moving_Average

V1 = 0x10
V2 = 0x20


class DeltaSol_BS_Plus():

    def_frames = (('S1', 'S2', '=HH'),
                  ('S3', 'S4', '=HH'),
                  ('SpeedRelay1', 'SpeedRelay2', 'Relaymask', 'Errormask', '=BBBB'),
                  ('SystemTime', 'Scheme', 'OptionsMask', '=HBB'),
                  ('RuntimeRelay1', 'RuntimeRelay2', '=HH'),
                  ('HeatQuantity_Wh', 'HeatQuantity_kWh', '=HH'),
                  ('HeatQuantity_MWh', 'Version', '=HH')
                  )

    def __init__(self, device, temperature_diff=0.2, temperature_avg_samples=5,
                 communication_timeout_seconds=30):
        self._device = device
        self.temperature_diff = temperature_diff
        self.communication_timeout_seconds = communication_timeout_seconds
        self._conn = None

        self._names = []
        for v in self.def_frames:
            self._names += v[:-1]

        self.S1 = None
        self.S1_ma = Moving_Average(temperature_avg_samples)
        self.S2 = None
        self.S2_ma = Moving_Average(temperature_avg_samples)
        self.S3 = None
        self.S3_ma = Moving_Average(temperature_avg_samples)
        self.S4 = None
        self.S4_ma = Moving_Average(temperature_avg_samples)
        self.SpeedRelay1 = None
        self.SpeedRelay2 = None
        self.Relaymask = None
        self.Errormask = None
        self.SystemTime = None
        self.Scheme = None
        self.OptionsMask = None
        self.RuntimeRelay1 = None
        self.RuntimeRelay2 = None
        self.HeatQuantity_Wh = None
        self.HeatQuantity_kWh = None
        self.HeatQuantity_MWh = None
        self.Version = None

        self.lastPacket = int(time.time() * 1000)

        self.on_change = None

    def normalize_value(self, key, value):
        """Convert a raw controller value and update its moving average if needed."""
        is_temperature = key.startswith('S') and len(key) == 2
        if not is_temperature:
            return value

        value *= 0.1
        moving_average = getattr(self, key + '_ma')
        moving_average.feed(value)
        return moving_average.get_avg()

    @classmethod
    def decode_bs_packet(cls, packet):
        """Decode one complete DeltaSol BS VBus packet without opening a serial port.

        Temperatures are returned in degrees Celsius. This small pure decoder lets
        recorded controller traffic exercise the protocol in tests.
        """
        if len(packet) != 52 or packet[0] != 0xaa:
            raise ValueError('expected a complete 52-byte VBus packet')

        destination, source, protocol = struct.unpack('=HHB', packet[1:6])
        command, frame_count, _header_crc = struct.unpack('=HBB', packet[6:10])
        if (destination, source, protocol, command, frame_count) != (
            0x0010, 0x4221, V1, 0x0100, 7
        ):
            raise ValueError('unsupported VBus packet')
        if cls.calc_crc(packet[1:10]) != 0:
            raise ValueError('invalid VBus packet header CRC')

        values = {}
        for index, definition in enumerate(cls.def_frames):
            frame = packet[10 + index * 6:16 + index * 6]
            if cls.calc_crc(frame) != 0:
                raise ValueError(f'invalid VBus frame CRC at index {index}')
            decoded = struct.unpack(definition[-1], cls.inject_septett(frame))
            for key, value in zip(definition[:-1], decoded):
                values[key] = round(value * 0.1, 1) if key.startswith('S') and len(key) == 2 else value

        return values

    @staticmethod
    def calc_crc(buffer):
        Crc = 0x7F
        for char in buffer:
            Crc = (Crc - char) & 0x7F
        return Crc

    @staticmethod
    def inject_septett(buffer):
        septett = buffer[4]
        return bytes([
            buffer[0] | 0x80 if septett & 1 else buffer[0],
            buffer[1] | 0x80 if septett & 2 else buffer[1],
            buffer[2] | 0x80 if septett & 4 else buffer[2],
            buffer[3] | 0x80 if septett & 8 else buffer[3]])

    def apply_decoded_values(self, values):
        """Publish a fully validated controller packet as one atomic update.

        VBus serial noise can produce bytes that resemble individual frames.
        Never publish any field until the header and every frame in the expected
        packet have passed CRC validation.
        """
        for key, value in values.items():
            old = getattr(self, key)
            is_temperature = key.startswith('S') and len(key) == 2
            if is_temperature:
                moving_average = getattr(self, key + '_ma')
                moving_average.feed(value)
                value = moving_average.get_avg()

            logging.debug("key=%s value=%s old=%s", key, value, old)
            if old == value:
                continue
            if is_temperature and old is not None and abs(old - value) < self.temperature_diff:
                continue
            if callable(self.on_change):
                self.on_change(key, value)
            setattr(self, key, value)

    def loop_forever(self):
        self._conn = serial.Serial(self._device, baudrate=9600, timeout=3.0)

        while True:
            if self._conn.read(1) != b'\xaa':
                if int(time.time() * 1000) - self.lastPacket > self.communication_timeout_seconds * 1000:
                    raise Exception('Broken communication')
                continue

            head_data = self._conn.read(5)
            if len(head_data) != 5:
                continue
            destination_address, source_address, protocol_version = struct.unpack('=HHB', head_data)
            if protocol_version != V1:
                # V2 packets have a different layout.  Their bytes stay below
                # the VBus sync marker, so resume scanning for the next packet
                # instead of consuming the following V1 packet as payload.
                continue

            head_data2 = self._conn.read(4)
            if len(head_data2) != 4 or self.calc_crc(head_data + head_data2) != 0:
                continue
            command, frame_count, _header_crc = struct.unpack('=HBB', head_data2)
            frame_data = self._conn.read(frame_count * 6)
            if len(frame_data) != frame_count * 6:
                continue
            if (destination_address, source_address, command, frame_count) != (0x0010, 0x4221, 0x0100, 7):
                continue

            try:
                values = self.decode_bs_packet(b'\xaa' + head_data + head_data2 + frame_data)
            except ValueError:
                # Ignore malformed traffic.  Crucially, do not refresh
                # lastPacket: a sustained bad stream remains unhealthy.
                continue

            self.apply_decoded_values(values)
            self.lastPacket = int(time.time() * 1000)

    def get_all_values(self):
        return {k: self.__dict__[k] for k in self._names}
