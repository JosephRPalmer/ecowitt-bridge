import logging


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def parse_string_to_dict(input_string):
    datapoints = {}
    pairs = input_string.replace("[", "").replace(
        "'", "").replace("]", "").split('&')

    for pair in pairs:
        key, value = pair.split('=')
        try:
            datapoints[key] = float(value)
        except ValueError:
            datapoints[key] = 0.0
            logging.warning("Non-numeric value for key {}: {}".format(key, value))

    return datapoints


def fahrenheit_to_celsius(fahrenheit):
    celsius = (fahrenheit - 32) * 5 / 9
    return celsius


def in_to_hpa(ins):
    hpa = ins * 33.6585
    return hpa
