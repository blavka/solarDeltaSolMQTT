import unittest
from solarDeltaSolMQTT.moving_average import Moving_Average


class TestMovingAverage(unittest.TestCase):

    def test_1_sample(self):
        mv = Moving_Average(5)
        mv.feed(10.0)

        self.assertEqual(mv.get_avg(), 10.0)

    def test_2_samples(self):
        mv = Moving_Average(5)
        mv.feed(10.0)
        mv.feed(5.0)

        self.assertEqual(mv.get_avg(), 7.5)

    def test_5_samples(self):
        mv = Moving_Average(5)
        mv.feed(60.0)
        mv.feed(60.2)
        mv.feed(60.0)
        mv.feed(60.2)
        mv.feed(60.0)

        self.assertEqual(mv.get_avg(), 60.08)

    def test_7_samples(self):
        mv = Moving_Average(5)
        mv.feed(1)
        mv.feed(2)
        mv.feed(60.0)
        mv.feed(60.2)
        mv.feed(60.0)
        mv.feed(60.2)
        mv.feed(60.0)

        self.assertEqual(mv.get_avg(), 60.08)
