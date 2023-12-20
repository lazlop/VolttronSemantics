"""
"""

__docformat__ = 'reStructuredText'

import logging
import sys
from sqlalchemy import create_engine, text
import pandas as pd
import yaml
import random
import json
from pytz import timezone
from datetime import datetime, timedelta, time
from volttron.platform.agent.utils import format_timestamp, get_aware_utc_now
from volttron.platform.messaging import headers as headers_mod
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC
from volttron.platform.scheduling import cron
from VolttronSemantics import application
from time import sleep
# import application

_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"

REQUESTER_ID = 'example-agent'

def exampleagent(config_path, **kwargs):

    _log.debug("Config path: {}".format(config_path))
    try:
        config = utils.load_config(config_path)
    except Exception:
        config = {}
    if not config:
        _log.info("Using Agent defaults for starting configuration.")
    _log.debug("config_dict before init: {}".format(config))

    return ExampleAgent(**kwargs)


class ExampleAgent(Agent):
    """
    Agent used to test the functionality of the CSV driver
    """


    def __init__(self, **kwargs):
        # Configure the base agent
        super(ExampleAgent, self).__init__(**kwargs)
        _log.debug("vip_identity: " + self.core.identity)
        self.default_config = {}
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"])

    def configure(self, config_name, action, contents):
        """
        Called after the Agent has connected to the message bus.
        If a configuration exists at startup this will be called before onstart

        Is called every time the configuration in the store changes.
        """
        self.config = self.default_config.copy()
        self.config.update(contents)

        _log.debug("Configuring Agent")

        self.frequency = self.config.get('frequency', 15)
        self.core.schedule(cron('*/{} * * * *'.format(self.frequency)),
                           self.control_runner)
        self.control_runner()

    def control_runner(self):
        print('############ running app ##############')
        self.update_steps()
        price, price_next_hour, TSetMax, TSetMin = self.get_parameters()
        TZonValues, TsetZonValues = self.query_database()
        setpoints = application.main(
            list(TZonValues.values()), list(TsetZonValues.values()), list(self.equip),
            price, price_next_hour, 
            self.steps, TSetMin, TSetMax
        )
        self.update_events(setpoints)
        _log.debug(f"event returned, setpoints are {setpoints}")
        return setpoints

    def update_events(self, setpoints): 
        for i, val in enumerate(setpoints):
            if (val[1] == 1) & (self.event_starts[i] == None):
                self.event_starts[i] = get_aware_utc_now()
            else:
                self.event_starts[i] = None
    
    def update_steps(self): 
        for i, start in enumerate(self.event_starts):
            if start == None:
                self.steps[i] = 0
            else:
                step = (get_aware_utc_now() - start).total_seconds()
                self.steps[i] = step
            print(self.steps[i])

    def add_baseline_values(self, setpoints):
        baseline = self.format_baseline_points(self.baseline_df)
        baseline_dict = [x[1] for x in baseline]
        for i, val in enumerate(setpoints):
            if val[1] == 0:
                setpoints[i] = (baseline_dict[i], 0)
        return setpoints

    def format_app_points(self, point_lst):
        message = []
        for i, val in enumerate(point_lst):
            message.append((str(self.TsetZonPoint[i]),int(round(val[0]))))
        _log.debug(f"app format {message}")
        return message 

    def save_points(self, data):
        # will save points to db using analysis/shadowmode topic
        header_time = get_aware_utc_now()
        metadata_dict = {}
        data = {x[0]:x[1] for x in data}
        for key in data.keys():
            metadata_dict[key] = {'units': 'C', 'tz': 'UTC', 'type': 'float'}
        
        headers = {
            headers_mod.DATE: format_timestamp(header_time),
            headers_mod.TIMESTAMP: format_timestamp(header_time)
        }

        topic = 'analysis/example/shadowmode'

        message = [data, metadata_dict]
        self._publish_wrapper(topic, headers, message)

    def get_parameters(self):
        now = datetime.now()
        print(now)
        next_hour = now.hour + 1 if now.hour < 23 else 0
        price = application.price_schedule[now.hour]
        price_next_hour = application.price_schedule[next_hour]
        TSetMax = application.TSetMax_baseline_schedule[now.hour]
        TSetMin = application.TSetMin_baseline_schedule[now.hour]
        print(price, price_next_hour, TSetMax, TSetMin)
        return price, price_next_hour, TSetMax, TSetMin
    

    def actuate(self,point_setting):
        print('actuating')
        start = datetime.now()
        end = datetime.now() + timedelta(minutes = self.frequency - 1)
        priority = 'LOW'
        task_id = str(random.randint(0,100000))
        devices = ['devices/sensibo/FCU1','devices/sensibo/FCU2','devices/sensibo/FCU3','devices/sensibo/FCU4','devices/sensibo/FCU5',
            'devices/ecobeeOffice','devices/ecobeeMainFloor'] 

        msg = [ [device, utils.format_timestamp(start), utils.format_timestamp(end)] for device in devices]
        try:
            result = self.vip.rpc.call('platform.actuator',
                                        'request_new_schedule',
                                           REQUESTER_ID,
                                           task_id,
                                           priority,
                                           msg).get(timeout=10)
        except Exception as e:
            print(e)
            _log.warning("Could not contact actuator. Is it running?")
        #_log.info("schedule result {}".format(result))

        print(point_setting)
        result = self.vip.rpc.call('platform.actuator',
                                    'set_multiple_points',
                                    REQUESTER_ID,
                                    point_setting).get(timeout=20)

    def _publish_wrapper(self, topic, headers, message):
        while True:
            try:
                _log.debug("publishing: " + topic)
                self.vip.pubsub.publish('pubsub',
                                        topic,
                                        headers=headers,
                                        message=message).get(timeout=10.0)

                _log.debug("finish publishing: " + topic)
            except gevent.Timeout:
                _log.warning("Did not receive confirmation of publish to "+topic)
                break
            except Again:
                _log.warning("publish delayed: " + topic + " pubsub is busy")
                gevent.sleep(random.random())
            except VIPError as ex:
                _log.warning("driver failed to publish " + topic + ": " + str(ex))
                break
            else:
                break
            
    def query_database(self):
        print('RAN FUNC')
        temps = self.vip.rpc.call("sqlhistorianagent-4.0.0_1", "query", 
            # ["sensibo/FCU1/Temperature","sensibo/FCU2/Temperature","sensibo/FCU3/Temperature","sensibo/FCU4/Temperature","sensibo/FCU5/Temperature"],
            self.TZonPoint,  
            start = format_timestamp(get_aware_utc_now() - timedelta(minutes  = 10)),
            end = format_timestamp(get_aware_utc_now()),
            order = "LAST_TO_FIRST",
            count = 1
            )
        
        setpoints = self.vip.rpc.call("sqlhistorianagent-4.0.0_1", "query", 
            # ["sensibo/FCU1/targetTemperature","sensibo/FCU2/targetTemperature","sensibo/FCU3/targetTemperature","sensibo/FCU4/targetTemperature","sensibo/FCU5/targetTemperature"], 
            self.TsetZonPoint,
            start = format_timestamp(get_aware_utc_now() - timedelta(minutes  = 10)),
            end = format_timestamp(get_aware_utc_now()),
            order = "LAST_TO_FIRST",
            count = 1
            )

        temps = { k: v[0][1] for k, v in temps.wait()['values'].items() }
        setpoints = { k: v[0][1] for k, v in setpoints.wait()['values'].items() }

        _log.debug([temps, setpoints])
        return temps, setpoints

def main():
    """Main method called to start the agent."""
    utils.vip_main(exampleagent,
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass

