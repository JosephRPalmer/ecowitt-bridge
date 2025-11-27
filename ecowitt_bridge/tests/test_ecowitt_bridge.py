import unittest
from unittest.mock import patch, MagicMock
from utils import fahrenheit_to_celsius, in_to_hpa, parse_string_to_dict
from prometheus_client import Gauge

class TestEcowittBridge(unittest.TestCase):

    def test_fahrenheit_to_celsius(self):
        self.assertAlmostEqual(fahrenheit_to_celsius(32), 0)
        self.assertAlmostEqual(fahrenheit_to_celsius(212), 100)
        self.assertAlmostEqual(fahrenheit_to_celsius(98.6), 37)

    def test_in_to_hpa(self):
        self.assertAlmostEqual(in_to_hpa(29.92125), 1007.104, places=2)

    def test_parse_string_to_dict(self):
        input_str = "['tempf=70.0&humidity=50&windspeedmph=10']"
        expected_dict = {'tempf': 70.0, 'humidity': 50.0, 'windspeedmph': 10.0}
        self.assertEqual(parse_string_to_dict(input_str), expected_dict)

        input_str_with_non_numeric = "['tempf=70.0&stationtype=GW1000']"
        expected_dict_non_numeric = {'tempf': 70.0, 'stationtype': 0.0}
        self.assertEqual(parse_string_to_dict(input_str_with_non_numeric), expected_dict_non_numeric)


if __name__ == '__main__':
    unittest.main()
