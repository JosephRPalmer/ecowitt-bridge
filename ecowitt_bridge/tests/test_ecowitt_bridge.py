import unittest
from unittest.mock import patch, MagicMock
from ecowitt_bridge import fahrenheit_to_celsius, in_to_hpa, parse_string_to_dict, update_gauge


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

    @patch('ecowitt_bridge.Gauge')
    def test_update_gauge(self, mock_gauge):
        gauges = {}
        # Test creating a new gauge
        update_gauge("new_metric", 123.45, gauges=gauges)
        self.assertIn("new_metric", gauges)
        mock_gauge.assert_called_with("new_metric", 'ECOWITT data gauge')
        gauges["new_metric"].set.assert_called_with(123.45)

        # Test updating an existing gauge
        mock_gauge.reset_mock()
        gauges["new_metric"].reset_mock()
        update_gauge("new_metric", 543.21, gauges=gauges)
        mock_gauge.assert_not_called() # Should not create a new one
        gauges["new_metric"].set.assert_called_with(543.21)


if __name__ == '__main__':
    unittest.main()
