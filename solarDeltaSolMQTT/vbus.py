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
                  ('SystemTime', 'Scheme', 'OptionsMas', '=HBB'),
                  ('RuntimeRelay1', 'RuntimeRelay2', '=HH'),
                  ('HeatQuantity_Wh', 'HeatQuantity_kWh', '=HH'),
                  ('HeatQuantity_MWh', 'Version', '=HH')
                  )

    def __init__(self, device, temperature_diff=0.2, temperature_avg_samples=5):
        self._device = device
        self.temperature_diff = temperature_diff
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

    def calc_crc(self, buffer):
        Crc = 0x7F
        for char in buffer:
            Crc = (Crc - char) & 0x7F
        return Crc

    def inject_septett(self, buffer):
        septett = buffer[4]
        return bytes([
            buffer[0] | 0x80 if septett & 1 else buffer[0],
            buffer[1] | 0x80 if septett & 2 else buffer[1],
            buffer[2] | 0x80 if septett & 4 else buffer[2],
            buffer[3] | 0x80 if septett & 8 else buffer[3]])

    def loop_forever(self):
        self._conn = serial.Serial(self._device, baudrate=9600, timeout=3.0)

        while 1:
            d = self._conn.read(1)
            if d == b'\xaa':
                # print("====MESS====")
                head_data = self._conn.read(5)
                destination_address, source_address, protocol_version = struct.unpack(
                    '=HHB', head_data)
                # print( destination_address, source_address, protocol_version )
                if protocol_version == V1:
                    head_data2 = self._conn.read(4)
                    command, frame_count, header_CRC = struct.unpack(
                        '=HBB', head_data2)
                    if self.calc_crc(head_data + head_data2) != 0:
                        continue

                    ts = int(time.time() * 1000)

                    if destination_address == 0x0010 and source_address == 0x4221 and command == 0x0100:
                        for i in range(frame_count):
                            frame_data = self._conn.read(6)
                            if self.calc_crc(frame_data) != 0:
                                break
                            data = self.inject_septett(frame_data)
                            def_frame = self.def_frames[i]
                            unpack_data = struct.unpack(def_frame[-1], data)
                            for j in range(len(def_frame) - 1):
                                key = def_frame[j]
                                value = unpack_data[j]
                                old = self.__dict__.get(key, None)

                                is_temperature = key[0] == 'S' and len(key) == 2

                                if is_temperature:
                                    value = value * 0.1
                                    ma = self.__dict__.get(key + '_ma')
                                    ma.feed(value * 0.1)
                                    value = ma.get_avg()

                                logging.debug(
                                    "key=%s value=%s old=%s", key, value, old)

                                if old == value:
                                    continue

                                if is_temperature and old and abs(old - value) < self.temperature_diff:
                                    continue

                                if callable(self.on_change):
                                    self.on_change(key, value)

                                self.__setattr__(key, value)

                    self.lastPacket = ts
            else:
                ts = int(time.time() * 1000)
                if ts - self.lastPacket > 10000:
                    raise Exception('Broken communication')

    def get_all_values(self):
        return {k: self.__dict__[k] for k in self._names}
