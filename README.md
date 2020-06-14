# Solar controller DeltaSol® BS series MQTT

[![Travis](https://travis-ci.org/blavka/solarDeltaSolMQTT.svg?branch=master)](https://travis-ci.org/blavka/solarDeltaSolMQTT)
[![Release](https://img.shields.io/github/release/blavka/solarDeltaSolMQTT.svg)](https://github.com/blavka/solarDeltaSolMQTT/releases)
[![License](https://img.shields.io/github/license/blavka/solarDeltaSolMQTT.svg)](https://github.com/blavka/solarDeltaSolMQTT/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/solarDeltaSolMQTT.svg)](https://pypi.org/project/solarDeltaSolMQTT)

## Installing

You can install **solarDeltaSolMQTT** directly from PyPI:

```sh
sudo pip3 install -U solarDeltaSolMQTT
```

## Config

Insert this snippet to the file /etc/solarDeltaSolMQTT.yml:

```yml
---
solar:
  device: /dev/ttyUSB1
mqtt:
  host: 127.0.0.1
  port: 1883
  prefix: solar
publish:
  S1: collector/temperature
  S2: boiler-bottom/temperature
  S3: boiler-top/temperature
  S4: return/temperature
  SpeedRelay1: pump/speed
  Errormask: true
```

## Usage

Update /etc/solarDeltaSolMQTT.yml and run

```sh
solarDeltaSolMQTT -c /etc/solarDeltaSolMQTT.yml
```

## Systemd

Insert this snippet to the file /etc/systemd/system/solarDeltaSolMQTT.service:

```
[Unit]
Description=solarDeltaSolMQTT
After=network.target

[Service]
Type=simple
User=pi
ExecStart=/usr/local/bin/solarDeltaSolMQTT -c /etc/solarDeltaSolMQTT.yml
Restart=always
RestartSec=5
StartLimitIntervalSec=0

[Install]
WantedBy=multi-user.target
```

Enable the service start on boot:

```sh
sudo systemctl enable solarDeltaSolMQTT.service
```

Start the service:

```sh
sudo systemctl start solarDeltaSolMQTT.service
```

View the service log:

```sh
journalctl -u solarDeltaSolMQTT.service -f
```

## PM2

```sh
pm2 start /usr/bin/python3 --name "solarDeltaSolMQTT" -- /usr/local/bin/solarDeltaSolMQTT -c /etc/solarDeltaSolMQTT.yml
pm2 save
```

## Development

```
git clone git@github.com:blavka/solarDeltaSolMQTT.git
cd solarDeltaSolMQTT
./test.sh
sudo python3 setup.py develop
```
