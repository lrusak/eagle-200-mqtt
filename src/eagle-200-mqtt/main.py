#!/usr/bin/env python3

import argparse
import libeagle
import signal
import time
import paho.mqtt.client as mqtt
import logging
import sys

import urllib

class EagleContext(object):
  def __init__(self, args):
    self.delay = args.interval # seconds
    self.stop = False

    self.log = logging.getLogger("shairport-display")

    self.format = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s', "%Y-%m-%d %H:%M:%S")

    self.handler = logging.StreamHandler(stream=sys.stdout)
    self.handler.setFormatter(self.format)
    self.handler.setLevel(logging.DEBUG)

    self.log.addHandler(self.handler)
    self.log.setLevel(logging.DEBUG)

    self.log.info("Starting application")

    self.conn = libeagle.Connection(args.eagle_ip, args.eagle_cloud_id, args.eagle_install_code)
    self.devices = self.conn.device_list()
    self.address = self.devices[0]["HardwareAddress"]
    self.details = self.conn.device_details(self.address)
    self.name = self.details[0]["Name"]
    self.variables = self.details[0]["Variables"][0]

    self.client = mqtt.Client("eagle-200-mqtt", True, None, mqtt.MQTTv31)
    self.client.on_connect = self.on_connect
    self.client.on_message = self.on_message
    self.client.connect(args.mqtt_ip, args.mqtt_port)
    self.client.loop_start()

    while not self.client.is_connected():
      self.log.info("Connecting to MQTT broker...")
      time.sleep(5)

  def on_connect(self, client, userdata, flags, rc):
    self.log.info("Connected to MQTT broker")

  def on_message(self, client, userata, flags, rc):
    self.log.info("Message recieved")

  def power_reading_loop(self):
    self.log.info("Starting loop")

    end_time = 0.0

    while not self.stop:

      start_time = time.monotonic()

      if (start_time - end_time) < self.delay:
        time.sleep(0.5)
        continue

      end_time = time.monotonic()

      try:
        query = self.conn.device_query(self.address, self.name, self.variables)
      except (urllib.error.HTTPError, OSError):
        self.log.error(f"Failed to query devices. Retrying in {self.delay}s")
        continue

      try:
        demand = float(query[0]["Variables"]["zigbee:InstantaneousDemand"]) * 1000.0
      except ValueError:
        self.log.error(f"Query empty. Retrying in {self.delay}s")
        continue

      self.log.info(f'{demand} W')
      self.client.publish("power/home", f"power,location=home,sensor=eagle-200 value={demand}")

    self.log.info("Stopping application")

  def quit(self):
    self.stop = True
    self.client.loop_stop()

def main():
  parser = argparse.ArgumentParser(description='Send power information from an eagle-200 to an MQTT broker', formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  required = parser.add_argument_group('required arguments')
  optional = parser.add_argument_group('optional arguments')

  required.add_argument('--eagle-ip', dest='eagle_ip', default=argparse.SUPPRESS, required=True, help='IP address of the eagle-200 device')
  required.add_argument('--eagle-cloud-id', dest='eagle_cloud_id', default=argparse.SUPPRESS, required=True, help='eagle-200 cloud id')
  required.add_argument('--eagle-install-code', dest='eagle_install_code', default=argparse.SUPPRESS, required=True, help='eagle-200 install code')

  required.add_argument('--mqtt-ip', dest='mqtt_ip', default=argparse.SUPPRESS, required=True, help='IP address of the mqtt broker')
  optional.add_argument('--mqtt-port', dest='mqtt_port', type=int, default=1883, help='Port of the mqtt broker')

  optional.add_argument('--interval', dest='interval', type=int, default=5, help='Interval in seconds')

  args = parser.parse_args()

  app = EagleContext(args)
  signal.signal(signal.SIGINT, lambda *args: app.quit())

  app.power_reading_loop()

if __name__ == '__main__':
  main()
