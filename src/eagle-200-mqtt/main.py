#!/usr/bin/env python3

import argparse
import libeagle
import signal
import asyncio
import aiomqtt
import logging
import sys

class EagleContext(object):

    def __init__(self, args) -> None:
        self.interval = args.interval # seconds
        self.eagle_ip = args.eagle_ip
        self.eagle_cloud_id = args.eagle_cloud_id
        self.eagle_install_code = args.eagle_install_code
        self.mqtt_ip = args.mqtt_ip
        self.mqtt_port = args.mqtt_port

        self.format = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s', "%Y-%m-%d %H:%M:%S")

        self.handler = logging.StreamHandler(stream=sys.stdout)
        self.handler.setFormatter(self.format)
        self.handler.setLevel(logging.INFO)

        self.log = logging.getLogger(__name__)
        self.log.addHandler(self.handler)
        self.log.setLevel(logging.INFO)

        self.log.info("Starting application")

    async def power_reading_loop(self) -> None:
        self.log.info("Starting loop")

        try:
            async with libeagle.Connection(self.eagle_ip, self.eagle_cloud_id, self.eagle_install_code) as conn:

                while True:

                    devices = await conn.device_list()

                    if len(devices) > 0:
                        break

                    asyncio.sleep(self.interval)

                device = next(x for x in devices if x["Name"] == "Power Meter")

                while True:
                    try:
                        async with aiomqtt.Client(hostname=self.mqtt_ip, port=self.mqtt_port) as client:

                            while True:

                                query = await conn.device_query(device["HardwareAddress"], "Main", "zigbee:InstantaneousDemand")

                                if len(query) > 0 and len(query["Components"]) > 0:

                                    component = next(x for x in query["Components"] if x["Name"] == "Main")

                                    demand = component["Variables"]["zigbee:InstantaneousDemand"]

                                    power = float(demand) * 1000.0
                                    self.log.info(f"{power} W")
                                    await client.publish("power/home", f"power,location=home,sensor=eagle-200 value={power}")

                                await asyncio.sleep(self.interval)

                    except aiomqtt.exceptions.MqttError:
                        print(f"Connection lost; Reconnecting in {self.interval} seconds ...")

                    await asyncio.sleep(self.interval)

        except asyncio.exceptions.CancelledError:
            pass
        finally:
            self.log.info("Stopping application")

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

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    task = asyncio.ensure_future(app.power_reading_loop())

    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGQUIT):
        loop.add_signal_handler(signum, lambda: task.cancel())

    loop.run_until_complete(task)

if __name__ == '__main__':
    sys.exit(main())
