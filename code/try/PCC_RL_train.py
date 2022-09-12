"""
This demo aims to help player running system quickly by using the pypi library simple-emualtor https://pypi.org/project/simple-emulator/.
"""
from simple_emulator import CongestionControl

# We provided a simple algorithms about block selection to help you being familiar with this competition.
# In this example, it will select the block according to block's created time first and radio of rest life time to deadline secondly.
from simple_emulator import BlockSelection

# We provided some simple algorithms about congestion control to help you being familiar with this competition.
# Like Reno and an example about reinforcement learning implemented by tensorflow
from simple_emulator import Reno

from simple_emulator import SimpleEmulator, create_emulator

# We provided some function of plotting to make you analyze result easily in utils.py
from simple_emulator import analyze_emulator, plot_rate
from simple_emulator import constant

from simple_emulator import cal_qoe

import gym.envs.algorithmic
import tensorflow as tf
from simple_arg_parse import arg_or_default
import os
import sys
import inspect
import json
import gym
from gym import spaces
from gym.utils import seeding
from gym.envs.registration import register
import numpy as np
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
import time
EVENT_TYPE_FINISHED='F'
EVENT_TYPE_DROP='D'
EVENT_TYPE_TEMP='T'
DELTA_SCALE = arg_or_default("--delta-scale", 0.025)


send_rate=1000
observations = np.zeros(40)
total_rtt=0
packet_count=0
get_count=0

# Your solution should include block selection and bandwidth estimator.
# We recommend you to achieve it by inherit the objects we provided and overwritten necessary method.
class MySolution(BlockSelection, Reno):

    def __init__(self):
        super().__init__()
        # base parameters in CongestionControl

        # the value of congestion window
        self.cwnd = 1
        # the value of sending rate
        self.send_rate = 10000
        # the value of pacing rate
        self.pacing_rate = float("inf")
        # use cwnd
        self.USE_CWND=False

        # for reno
        self.ssthresh = float("inf")
        self.curr_state = "slow_start"
        self.states = ["slow_start", "congestion_avoidance", "fast_recovery"]
        # the number of lost packets
        self.drop_nums = 0
        # the number of acknowledgement packets
        self.ack_nums = 0

        # current time
        self.cur_time = -1
        # the value of cwnd at last packet event
        self.last_cwnd = 0
        # the number of lost packets received at the current moment
        self.instant_drop_nums = 0

    def select_block(self, cur_time, block_queue):
        '''
        The alogrithm to select the block which will be sended in next.
        The following example is selecting block by the create time firstly, and radio of rest life time to deadline secondly.
        :param cur_time: float
        :param block_queue: the list of Block.You can get more detail about Block in objects/block.py
        :return: int
        '''
        def is_better(block):
            best_block_create_time = best_block.block_info["Create_time"]
            cur_block_create_time = block.block_info["Create_time"]
            # if block is miss ddl
            if (cur_time - cur_block_create_time) >= block.block_info["Deadline"]:
                return False
            if (cur_time - best_block_create_time) >= best_block.block_info["Deadline"]:
                return True
            if best_block_create_time != cur_block_create_time:
                return best_block_create_time > cur_block_create_time
            return (cur_time - best_block_create_time) * best_block.block_info["Deadline"] > \
                   (cur_time - cur_block_create_time) * block.block_info["Deadline"]

        best_block_idx = -1
        best_block= None
        for idx, item in enumerate(block_queue):
            if best_block is None or is_better(item) :
                best_block_idx = idx
                best_block = item

        return best_block_idx

    def print1(self):
        return 1

    def on_packet_sent(self, cur_time):
        """
        The part of solution to update the states of the algorithm when sender need to send packet.
        """
        global send_rate
        output = {
            "cwnd" : self.cwnd,
            "send_rate" : send_rate,
            "extra" : { }
        }

        return output

    def cc_trigger(self, cur_time, event_info):
        """
        The part of algorithm to make congestion control, which will be call when sender get an event about acknowledge or lost from reciever.
        See more at https://github.com/AItransCompetition/simple_emulator/tree/master#congestion_control_algorithmpy.
        """
        packet_time=event_info['packet_information_dict']['Create_time']
        event_type = event_info["event_type"]
        event_time = cur_time

        
        global send_rate,packet_count,get_count,total_rtt,observations
        # set cwnd or sending rate in sender
        packet_count+=1
        if event_type==EVENT_TYPE_FINISHED:
            get_count+=1
            total_rtt+=event_time-packet_time
            observations=np.append(observations,[1,event_time-packet_time])
            observations=np.delete(observations,[0,1])
        else:
            observations=np.append(observations,[0,event_time-packet_time])
            observations=np.delete(observations,[0,1])

        

        return {
            "cwnd" : self.cwnd,
            "send_rate" : send_rate,
        }


class SimulatedNetworkEnv(gym.Env):
    
    def __init__(self,
                 history_len=arg_or_default("--history-len", default=20),
                 features=arg_or_default("--input-features",
                    default="sent latency inflation,"
                          + "latency ratio,"
                          + "send ratio")):
        self.emulator = create_emulator(
            block_file=["datasets/scenario_1/blocks/block-priority-0.csv", "datasets/scenario_1/blocks/block-priority-1.csv","datasets/scenario_1/blocks/block-priority-2.csv"],
            second_block_file=["datasets/background_traffic_traces/web.csv"],
            trace_file="datasets/scenario_1/networks/traces_23.txt",
            solution=MySolution(),
            # enable logging packet. You can train faster if ENABLE_LOG=False
            ENABLE_LOG=False
        )
        self.history_len=history_len
        self.action_space = spaces.Box(np.array([-1e12]), np.array([1e12]), dtype=np.float32)
        self.observation_space = None
        self.observation_space=spaces.Box(np.tile([0,1], self.history_len),
                                            np.tile([1,0], self.history_len),
                                            dtype=np.float32)
        self.count=0
        self.total_step=150
        self.reward=0

    def step(self, actions):
        global send_rate,total_rtt,packet_count,get_count,observations
        self.count+=1

        action = actions
        delta=action[0]
        delta *= DELTA_SCALE
        if delta >= 0.0:
            send_rate*= (1.0 + delta)
        else:
            send_rate/= (1.0 + delta)
        self.emulator.run_for_dur(0.1)

        if get_count!=0:
            self.reward+=get_count-100*(total_rtt/get_count)-20*(1-get_count/packet_count)
        else:
            self.reward=0
        total_rtt=0
        packet_count=0
        get_count=0
        # print(send_rate)
        

        return observations,self.reward,(self.count>=self.total_step),{}

    def reset(self):
        print("reward",self.reward)
        self.emulator = create_emulator(
            block_file=["datasets/scenario_1/blocks/block-priority-0.csv", "datasets/scenario_1/blocks/block-priority-1.csv","datasets/scenario_1/blocks/block-priority-2.csv"],
            second_block_file=["datasets/background_traffic_traces/web.csv"],
            trace_file="datasets/scenario_1/networks/traces_23.txt",
            solution=MySolution(),
            # enable logging packet. You can train faster if ENABLE_LOG=False
            ENABLE_LOG=False
        )
        global observations
        observations=np.zeros(40)
        self.count=0
        reward=0
        self.reward=0
        return observations


    def render(self, mode='human'):
        pass

    def dump_events_to_file(self, filename):
        with open(filename, 'w') as f:
            json.dump(self.event_record, f, indent=4)

register(id='PccRL-v0', entry_point='PCC_RL_train:SimulatedNetworkEnv')
