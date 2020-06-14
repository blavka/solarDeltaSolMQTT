#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import click
import click_log
import logging
import os
import sys
from .mqtt_client import MqttClient
from .config import load_config
from .vbus import DeltaSol_BS_Plus

__version__ = '0.0.0'


@click.command()
@click.version_option(version=__version__)
@click.option('--config', '-c', 'config_file', type=click.File('r'), required=True, help='configuration file (YAML format).')
@click_log.simple_verbosity_option(default='INFO')
def cli(config_file=None):
    logging.info('Process started')
    config = load_config(config_file)
    try:
        publish = config.get('publish', None)
        logging.debug('publish %s', publish)

        solar = DeltaSol_BS_Plus(**config['solar'])

        mqtt = MqttClient(**config['mqtt'])
        mqtt.loop_start()

        def on_change(key, value):
            if isinstance(value, float):
                value = '%.1f' % value
            else:
                value = str(value)

            logging.info("Change %s %s", key, value)

            if publish is None:
                return mqtt.publish(key, value, use_json=False)

            tmp = publish.get(key, None)
            if not tmp:
                return

            if isinstance(tmp, str):
                mqtt.publish(tmp, value, use_json=False)
            else:
                mqtt.publish(key, value, use_json=False)

        solar.on_change = on_change

        solar.loop_forever()

    except KeyboardInterrupt:
        logging.warn('KeyboardInterrupt')
    except Exception as e:
        click.echo(str(e), err=True)
        if os.environ.get('DEBUG', False):
            raise e
        sys.exit(1)

    logging.info('Process stopped')


def main():
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s')
    cli()
