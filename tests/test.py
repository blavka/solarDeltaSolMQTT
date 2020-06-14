import unittest
from solarDeltaSolMQTT.config import load_config, ConfigError
import io


class TestCongig(unittest.TestCase):

    def test_default(self):
        fd = io.StringIO("""
solar:
  device: /dev/ttyUSB0
""")

        config = load_config(fd)

        self.assertEqual(config['solar']['device'], '/dev/ttyUSB0')
        self.assertEqual(config['solar']['temperature_diff'], 0.2)
        self.assertEqual(config['solar']['temperature_avg_samples'], 8)
        self.assertEqual(config['mqtt']['host'], '127.0.0.1')
        self.assertEqual(config['mqtt']['port'], 1883)
        self.assertEqual(config['mqtt']['prefix'], 'solar')

    def test_custom(self):
        fd = io.StringIO("""
solar:
  device: /dev/ttyUSB0
mqtt:
  host: 192.168.0.1
  port: 1990
  prefix: aaa
""")

        config = load_config(fd)

        self.assertEqual(config['solar']['device'], '/dev/ttyUSB0')
        self.assertEqual(config['solar']['temperature_diff'], 0.2)
        self.assertEqual(config['mqtt']['host'], '192.168.0.1')
        self.assertEqual(config['mqtt']['port'], 1990)
        self.assertEqual(config['mqtt']['prefix'], 'aaa')

    def test_missing_solar_key(self):
        fd = io.StringIO("""
mqtt:
  host: 192.168.0.1
""")
        with self.assertRaises(ConfigError) as cm:
            load_config(fd)
        self.assertEqual(cm.exception.args[0], "Missing key: 'solar'")


if __name__ == '__main__':
    unittest.main()
