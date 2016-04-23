import socket
import json
from enum import Enum
from message import *

'''
getstatus/sendstatus
test timeouts
ballot for starting migration -- check quorums
ballot for migration agents
'''

class Island(object):
    def __init__(mid, my_agents, all_agents, mid_to_ports):
        '''
        :param mid_to_ports: tuple of (host, port) of machine with ID mid
        '''
        self.mid = mid
        self.my_agents = my_agents
        self.agents = agents 
        self.mid_to_sockets = {}

        for mid in mid_to_ports:
            self.mid_to_sockets[mid] = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.mid_to_sockets[mid].connect(mid_to_ports[mid])

    def get_all_agents(self):
        # at every migration, get all agents from live machines
        pass

    def run(self): 
        while(True):
            for _ in range(self.num_epochs):
                self.run_epoch()
            for mid in self.mid_to_sockets:
                status = self.get_status(mid)

    def run_epoch(self):
        pass

    def run_migration(self):
        # permute list
        # send list to all participating migration islands
        pass

    def send_status(self, receiver):
        '''
        Send the status of this island (alive, currently eovlving, ready to migrate, etc.
        to the indicated recipient

        :param receiver: The mid of the machine to which the status is sent
        :return: Success or failure of the send
        '''

        # listen for a GetStatus message
        # pretty sure this doesn't work
        resp = recv_msg(MsgLen.GETSTATUS)
        resp_dict = decode_msg(resp)

        # create a status message and send to the requester
        msg = create_msg(self.mid, Action.SENDSTATUS)#add stuff to this
        send_msg(msg, self.mid_to_sockets[resp_dict['mid']])

    def get_status(self, destination):
        '''
        Get the status of the destination island

        :param destination: The mid of the machine whose status to get
        :return: status of the machine 
        '''

        msg = create_msg(self.mid, Action.GETSTATUS)
        try:
            send_msg(msg, len(msg))
            # pretty sure this doesn't work
            resp = recv_msg(MsgLen.SENDSTATUS)#len of status msg here
        except RuntimeError as e:
            #?
            pass
        

    def send_start_migration_ballot(self):
        '''
        Quorum (majority) need to agree to start this migration
        '''
        pass

    def accept_migration_and_send_agents(self):
        '''
        send back list of begin agents
        '''
        pass

    def send_migration_agents_ballot(self):
        pass

    def accept_migration_agents_ballot(self):
        pass
