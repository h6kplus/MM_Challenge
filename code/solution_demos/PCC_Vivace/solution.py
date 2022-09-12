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

EVENT_TYPE_FINISHED='F'
EVENT_TYPE_DROP='D'
EVENT_TYPE_TEMP='T'

# Your solution should include block selection and bandwidth estimator.
# We recommend you to achieve it by inherit the objects we provided and overwritten necessary method.
class MySolution(BlockSelection, Reno):

    def __init__(self):
        super().__init__()
        # base parameters in CongestionControl

        # the value of congestion window
        self.cwnd = 0
        # the value of sending rate
        self.send_rate = 200
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


        self.alpha=0.1
        self.nowRate=40 
        self.addRate=2
        self.now_phase = "begin_phase"
        self.ack_nums = 0
        self.rtt=0
        self.count=0
        self.s1=0
        self.x1=0
        self.rtt1=0
        self.l1=0
        self.s2=0
        self.x2=0
        self.rtt2=0
        self.l2=0
        self.cnt=0

        self.begin_time=0

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

    def on_packet_sent(self, cur_time):
        self.call_nums += 1

        if self.now_phase=="begin_phase":
            if(self.curr_state==self.states[0]):
                self.send_rate=self.nowRate
            elif(self.curr_state==self.states[1]):
                self.send_rate=self.nowRate*(1-self.alpha)
            print("rate1",self.send_rate)
            self.now_phase="find_rtt"
            self.s1=0
            self.begin_time=cur_time

        output = {
            "cwnd" : self.cwnd,
            "send_rate" : self.send_rate,
            "extra" : {"state":self.now_phase}
        }
        if (self.now_phase=="find_rtt1"):
            self.s1+=1;
        if (self.now_phase=="find_rtt2"):
            self.s2+=1;

        return output

    def cc_trigger(self, cur_time, event_info):
        """
        The part of algorithm to make congestion control, which will be call when sender get an event about acknowledge or lost from reciever.
        See more at https://github.com/AItransCompetition/simple_emulator/tree/master#congestion_control_algorithmpy.
        """
        packet_time=event_info['packet_information_dict']['Create_time']

        event_type = event_info["event_type"]
        event_time = cur_time
        self.rtt=event_time-packet_time
        if self.now_phase=="find_rtt":
            self.now_phase="find_rtt1"
            self.count+=1


            

        if ((event_info['packet_information_dict']["Extra"]["state"]=="find_rtt1" )& (self.now_phase=="find_rtt1")):
            self.x1=0
            self.rtt1=0
            self.l1=0
            self.now_phase="calculate_u1"
        if ((event_info['packet_information_dict']["Extra"]["state"]=="find_rtt1" )& (self.now_phase=="calculate_u1")):
            if event_type==EVENT_TYPE_FINISHED:
                self.x1+=1
                # print("send packet1",self.s1)
                # print("get packet1",self.x1)
                self.rtt1+=self.rtt
                # print("rtt1",self.rtt1)
            if event_type==EVENT_TYPE_DROP:
                self.l1+=1
                # print("lose",self.l1)

        
        if ((event_info['packet_information_dict']["Extra"]["state"]=="calculate_u1" )& (self.now_phase=="calculate_u1")):
            self.s1+=1
            if event_type==EVENT_TYPE_FINISHED:
                self.x1+=1
                print("send packet1",self.s1)
                print("get packet1",self.x1)
                self.rtt1+=self.rtt
                # print("rtt1",self.rtt1)
            if event_type==EVENT_TYPE_DROP:
                self.l1+=1
            self.t1=self.rtt
            print((self.x1/self.t1),-1000*(self.rtt1/self.x1),-200*(1-self.x1/self.s1))
            self.u1=(self.x1/self.t1)-1000*(self.rtt1/self.x1)-200*(1-self.x1/self.s1)
            print("u1",self.u1)
            if(self.curr_state==self.states[0]):
                self.send_rate*=self.addRate
            elif(self.curr_state==self.states[1]):
                self.send_rate=self.nowRate*(1+self.alpha)
            print("rate2",self.send_rate)
       
            self.now_phase="find_rtt2"
            self.s2=0

        if ((event_info['packet_information_dict']["Extra"]["state"]=="find_rtt2" )& (self.now_phase=="find_rtt2")):
            self.x2=0
            self.rtt2=0
            self.l2=0
       
            self.now_phase="calculate_u2"

        if ((event_info['packet_information_dict']["Extra"]["state"]=="find_rtt2" )& (self.now_phase=="calculate_u2")):
            if event_type==EVENT_TYPE_FINISHED:
                self.x2+=1
                # print("send packet2",self.s2)
                # print("get packet2",self.x2)
                self.rtt2+=self.rtt
                # print("rtt2",self.rtt2)
            if event_type==EVENT_TYPE_DROP:
                self.l2+=1
                # print("lose",self.l2)
            
        if ((event_info['packet_information_dict']["Extra"]["state"]=="calculate_u2" )& (self.now_phase=="calculate_u2")):
            self.s2+=1
            if event_type==EVENT_TYPE_FINISHED:
                self.x2+=1
                # print("send packet2",self.s2)
                # print("get packet2",self.x2)
                self.rtt2+=self.rtt
                # print("rtt2",self.rtt2)
            if event_type==EVENT_TYPE_DROP:
                self.l2+=1
            self.t2=self.rtt
            self.u2=(self.x2/self.t2)-1000*(self.rtt2/self.x2)-200*(1-self.x2/self.s2)
            print("u2",self.u2)
            print("count",self.count)
            if(self.curr_state==self.states[0]):
                if((self.u2>self.u1)):
                    self.nowRate=self.send_rate
                    self.cnt=0
                else:
                    if(self.cnt>3):
                        self.curr_state=self.states[1]
                    else:
                        self.cnt+=1
            elif(self.curr_state==self.states[1]):
                if(self.u2>self.u1):
                    self.nowRate*=(1+self.alpha)
                elif(self.u2<self.u1):
                    self.nowRate*=(1-self.alpha)

            print(self.nowRate)
                    
            self.now_phase="begin_phase"
            

        
            
        # print(event_time-self.begin_time)


        # if self.cur_time < event_time:
        #     # initial parameters at a new moment
        #     self.last_cwnd = 0
        #     self.instant_drop_nums = 0

        # # if packet is dropped
        # if event_type == EVENT_TYPE_DROP:
        #     # dropping more than one packet at a same time is considered one event of packet loss 
        #     if self.instant_drop_nums > 0:
        #         return
        #     self.instant_drop_nums += 1
        #     # step into fast recovery state
        #     self.curr_state = self.states[2]
        #     self.drop_nums += 1
        #     # clear acknowledgement count
        #     self.ack_nums = 0
        #     # Ref 1 : For ensuring the event type, drop or ack?
        #     self.cur_time = event_time
        #     if self.last_cwnd > 0 and self.last_cwnd != self.cwnd:
        #         # rollback to the old value of cwnd caused by acknowledgment first
        #         self.cwnd = self.last_cwnd
        #         self.last_cwnd = 0

        # # if packet is acknowledged
        # elif event_type == EVENT_TYPE_FINISHED:
        #     # Ref 1
        #     if event_time <= self.cur_time:
        #         return
        #     self.cur_time = event_time
        #     self.last_cwnd = self.cwnd

        #     # increase the number of acknowledgement packets
        #     self.ack_nums += 1
        #     # double cwnd in slow_start state
        #     if self.curr_state == self.states[0]:
        #         if self.ack_nums == self.cwnd:
        #             self.cwnd *= 2
        #             self.ack_nums = 0
        #         # step into congestion_avoidance state due to exceeding threshhold
        #         if self.cwnd >= self.ssthresh:
        #             self.curr_state = self.states[1]

        #     # increase cwnd linearly in congestion_avoidance state
        #     elif self.curr_state == self.states[1]:
        #         if self.ack_nums == self.cwnd:
        #             self.cwnd += 1
        #             self.ack_nums = 0

        # # reset threshhold and cwnd in fast_recovery state
        # if self.curr_state == self.states[2]:
        #     self.ssthresh = max(self.cwnd // 2, 1)
        #     self.cwnd = self.ssthresh
        #     self.curr_state = self.states[1]

        # set cwnd or sending rate in sender
        return {
            "cwnd" : self.cwnd,
            "send_rate" : self.send_rate,
        }