"""
"""

__docformat__ = 'reStructuredText'

import logging
import sys
from sqlalchemy import create_engine, text
import pandas as pd
import yaml
import json
from pytz import timezone
from datetime import datetime, timedelta, time
from volttron.platform.agent.utils import format_timestamp, get_aware_utc_now
from volttron.platform.messaging import headers as headers_mod
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC
from volttron.platform.scheduling import cron
from VolttronSemantics.application import query_model
from time import sleep
# import application

_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"


def brickdragent(config_path, **kwargs):

    _log.debug("Config path: {}".format(config_path))
    try:
        config = utils.load_config(config_path)
    except Exception:
        config = {}
    if not config:
        _log.info("Using Agent defaults for starting configuration.")
    _log.debug("config_dict before init: {}".format(config))

    return BrickDRAgent(**kwargs)


class BrickDRAgent(Agent):
    """
    Agent used to test the functionality of the CSV driver
    """


    def __init__(self, **kwargs):
        # Configure the base agent
        super(BrickDRAgent, self).__init__(**kwargs)
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
        sheet_url = self.config.get('sheet_url')
        #before committing move out urls
        self.schedule = self.config.get('schedule').replace(
            '/edit#gid=', '/export?format=csv&gid=')
        self.baseline = self.config.get('baseline').replace(
            '/edit#gid=', '/export?format=csv&gid=')
        self.prices = self.config.get('prices').replace(
            '/edit#gid=', '/export?format=csv&gid=')
        self.furnace = self.config.get('furnace').replace(
            '/edit#gid=', '/export?format=csv&gid=')

        self.model_path = self.config.get('model_path')

        self.TZonPoint, self.TsetZonPoint, self.equip = application.query_model(self.model_path)

        self.steps = [0 for i in range(len(self.TZonPoint))]
        self.event_starts = [ None for i in range(len(self.TZonPoint))]

        self.read_schedule()
        self.core.schedule(cron('0 */12 * * *'), self.control_runner)


        self.frequency = self.config.get('frequency', 15)
        self.core.schedule(cron('*/{} * * * *'.format(self.frequency)),
                           self.control_runner)
        self.control_runner()
        #Do I want to consistently write the unit? Once per day or each time I write?
        # Do I want to read the schedule every time?, or just once ? 
    
    def read_schedule(self):
        self.sched_df = pd.read_csv(self.schedule,
            parse_dates=True,
            index_col='Date')
        self.prices_df = pd.read_csv(self.prices,
                    index_col='Time')
        self.baseline_df = pd.read_csv(self.baseline,
                    index_col='Time')
        self.furnace_df = pd.read_csv(self.baseline,
                    index_col='Time')

    def control_runner(self):
        _log.debug('running controls')
        now = datetime.now()

        if now.strftime('%Y-%m-%d') not in self.sched_df.index:
            _log.debug('date not in schedule, using baseline controls')
            setpoints = self.format_baseline_points(self.baseline_df)
            self.actuate(setpoints)
            return

        #sometimes this google sheet seems to change, and I'll have to get rid of or add [0]
        try: 
            mode = self.sched_df.loc[now.strftime('%Y-%m-%d'), 'Mode']# [0]
        except Exception as e:
            _log.debug(e)
            mode = self.sched_df.loc[now.strftime('%Y-%m-%d'), 'Mode'][0]
            
        _log.debug(f'Mode is {mode}')
        if mode == "HeuristicShadowMode":
            try:
                setpoints = self.run_app()
                message = self.format_app_points(setpoints)
                self.save_points(message)
            except Exception as e:
                _log.debug(e)

            return
        if mode == "HeuristicApplication":
            try:
                setpoints = self.run_app()
                save_message = self.format_app_points(setpoints)
                self.save_points(save_message)

                setpoints_adj = self.add_baseline_values(setpoints)
                message = self.format_app_points(setpoints_adj)
                self.actuate(message)
                return

            except Exception as e:
                _log.debug(e)
                setpoints = self.format_baseline_points(self.baseline_df)
                self.actuate(setpoints)

            return

    def run_app(self):

        self.update_steps(self.event_starts)
        price, price_next_hour, TSetMax, TSetMin = self.get_parameters()
        TZonValues, TsetZonValues = self.query_database()

        setpoints = application.main(
            TZonValues, TsetZonValues, self.equip,
            price, price_next_hour, 
            self.steps, TSetMin, TSetMax
        )
        self.update_events(setpoints)
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
            message.append((self.TsetZonPoint[i],val[0]))
        message = message + self.format_baseline_points(self.furnace_df)
        _log.debug(message)
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

        topic = 'analysis/brickdr/shadowmode'

        message = [data, metadata_dict]
        self._publish_wrapper(topic, headers, message)
        _log.info('save_points complete')

    def get_parameters(self):
        now = datetime.now()
        price = self.prices_df.loc[now.hour]['Prices']
        price_next_hour = self.prices_df.loc[now.hour + 1]['Prices']
        TSetMax = price = self.prices_df.loc[now.hour]['TSetMax']
        TSetMin = price = self.prices_df.loc[now.hour]['TSetMin']
        return price, price_next_hour, TSetMax, TSetMin
    
    def format_baseline_points(self, df):
        now = datetime.now()
        setpoints = df.loc[now.hour]
        message = []

        for name, value in setpoints.items():
            if pd.isna(value):
                continue
            try:
                tup = (name, int(value))
            except:
                tup = (name, str(value))
            message.append(tup)

        _log.debug(message)
        return message

    def actuate(self,point_setting):
        return 

        # start = datetime.now()
        # end = datetime.now() + timedelta(minutes = self.frequency - 1)
        # priority = 'LOW'
        # task_id = TASK_ID
        # task_id = str(random.randint(0,100000))
        # devices = ['devices/sensibo/FCU1','devices/sensibo/FCU2','devices/sensibo/FCU3','devices/sensibo/FCU4','devices/sensibo/FCU5',
        #     'devices/ecobeeOffice','devices/ecobeeMainFloor'] 

        # msg = [ [device, utils.format_timestamp(start), utils.format_timestamp(end)] for device in devices]
        # try:
        #     result = self.vip.rpc.call('platform.actuator',
        #                                 'request_new_schedule',
        #                                    REQUESTER_ID,
        #                                    task_id,
        #                                    priority,
        #                                    msg).get(timeout=10)
        # except Exception as e:
        #     print(e)
        #     _log.warning("Could not contact actuator. Is it running?")
        # _log.info("schedule result {}".format(result))

        # print(point_setting)
        # result = self.vip.rpc.call('platform.actuator',
        #                             'set_multiple_points',
        #                             REQUESTER_ID,
        #                             point_setting).get(timeout=20)
        # print(result)    

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
            start = format_timestamp(get_aware_utc_now() - datetime.timedelta(minutes  = 10)),
            end = format_timestamp(get_aware_utc_now()),
            order = "LAST_TO_FIRST",
            count = 1
            )
        
        setpoints = self.vip.rpc.call("sqlhistorianagent-4.0.0_1", "query", 
            # ["sensibo/FCU1/targetTemperature","sensibo/FCU2/targetTemperature","sensibo/FCU3/targetTemperature","sensibo/FCU4/targetTemperature","sensibo/FCU5/targetTemperature"], 
            self.TsetZonPoint,
            start = format_timestamp(get_aware_utc_now() - datetime.timedelta(minutes  = 10)),
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
    utils.vip_main(brickdragent,
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass

