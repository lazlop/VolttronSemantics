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
        self.active_testing = self.config.get('active_testing').replace(
            '/edit#gid=', '/export?format=csv&gid=')

        self.frequency = self.config.get('frequency', 15)
        self.core.schedule(cron('*/{} * * * *'.format(self.frequency)),
                           self.control_runner)
        self.control_runner()
        #Do I want to consistently write the unit? Once per day or each time I write?
    
    def read_schedule(self):
        sched_df = pd.read_csv(self.schedule,
            parse_dates=True,
            index_col='Date')
        active_testing_df = pd.read_csv(self.active_testing,
                    index_col='Time')
        baseline_df = pd.read_csv(self.baseline,
                    index_col='Time')

        return sched_df, active_testing_df, baseline_df
    
    def control_runner(self):
        _log.debug('running controls')
        now = datetime.now()
        sched_df, active_testing_df, baseline_df  = self.read_schedule()
        if now.strftime('%Y-%m-%d') not in sched_df.index:
            _log.debug('date not in schedule, using baseline controls')
            self.write_baseline_points(baseline_df)
            return

        #sometimes this google sheet seems to change, and I'll have to get rid of or add [0]
        try: 
            mode = sched_df.loc[now.strftime('%Y-%m-%d'), 'Mode']# [0]
        except Exception as e:
            _log.debug(e)
            mode = sched_df.loc[now.strftime('%Y-%m-%d'), 'Mode'][0]
            
        _log.debug(f'Mode is {mode}')
        if mode == "HeuristicShadowMode":
            try:
                mpc_setpoints = run_app()
            except Exception as e:
                _log.debug('MPC has ERROR', e)

            return
        if mode == "HeuristicApplication":
            for i in range(0,2):    
                try:
                    mpc_setpoints = run_mpc()
                except Exception as e:
                    _log.debug(e)
                    # Wait and try again
                else:
                    self.write_mpc_points(mpc_setpoints)
                    return
                sleep(60)
            #self.write_points(baseline_df)
            return
        
    def write_mpc_points(self, point_dict):
        message = []
        for name,value in point_dict.items():
            print(name)
            message.append((name,value))

        _log.debug(message)
        self.actuate(message)

        #  print('running get data cws')
        # tz_local = timezone("America/Los_Angeles")
        # end = get_aware_utc_now().astimezone(tz_local)
        # start = end - datetime.timedelta(seconds=self.frequency)
        # header_time = get_aware_utc_now()
        # print('start: ', start, 'end: ', end)
        # cws_data = self.get_data_cws(self.flexq_login, self.flex_user, self.flex_password)
        # val_dict, metadata = self.filter_cws_data(cws_data, self.cws_point_map)
        # metadata_dict = {}
        # for key in metadata.keys():
        #     metadata_dict[key] = {'units': metadata[key], 'tz': 'UTC', 'type': 'float'}
        # headers = {
        #     headers_mod.DATE: format_timestamp(header_time),
        #     headers_mod.TIMESTAMP: format_timestamp(header_time)
        # }
        # topic = self.base_topic + 'all'
        # message = [val_dict, metadata_dict]
        # self._publish_wrapper(topic, headers, message)
        # _log.info('get_cws_data complete')



    
    def write_baseline_points(self, df):
        now = datetime.now()
        setpoints = df.loc[now.hour]
        # JOIN devices TO ALL TOPIC NAMES
        #message = [ ('devices/' + name, str(value) ) for name,value in setpoints.items() if not pd.isna(value) ]
        #message = [ (name, value ) for name,value in setpoints.items() if not pd.isna(value) ]
        message = []

        for name, value in setpoints.items():
            if pd.isna(value):
                continue
            try:
                tup = (name, int(value))
            except:
                tup = (name, str(value))
            message.append(tup)

        # type issue, need to make the value types certain python types?
        # make everything string or int
        #message = [('sensibo/FCU1/targetTemperature', int(70))]

        _log.debug(message)
        
        self.actuate(message)

        # for loop or multipoint write
        # for topic, value in setpoints.items():
        #     self.call_actuator(topic, value)

    def actuate(self,point_setting):
        #will have to schedule all devices
        # ON command should also be sent with MPC.
        start = datetime.now()
        end = datetime.now() + timedelta(minutes = self.frequency)
        priority = 'LOW'
        task_id = TASK_ID
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
        _log.info("schedule result {}".format(result))

        print(point_setting)
        result = self.vip.rpc.call('platform.actuator',
                                    'set_multiple_points',
                                    REQUESTER_ID,
                                    point_setting).get(timeout=20)
        print(result)    

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

                    # self.write_dr_point()
                    # self.dr_flag = False
                    # self.write_baseline()



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

