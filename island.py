import socket
import json
from enum import Enum

'''
getstatus/sendstatus
test timeouts
ballot for starting migration -- check quorums
ballot for migration agents

Protocol:

    All messages are json:

        mid: sender
        protocol version:
        action:
        args:
        kwargs:
'''

class Action(Enum):
    GETSTATUS = 0
    SENDSTATUS = 1
    '''
    TODO
    SEND_START_MIGRATION = 2
    ACCEPT_START_MIGRATION = 3
    '''

def create_msg(mid, action, *args, **kwargs):
    return json.dumps({
        'mid': mid,
        'version': 0,
        'action': action,
        'args': args,
        'kwargs': kwargs
    })
    
def decode_msg(msg):
    return json.loads(msg)

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
        pass

    def get_status(self, destination):
        '''
        Get the status of the destination island

        :param destination: The mid of the machine whose status to get
        :return: status of the machine 
        '''

        msg = create_msg(self.mid, Action.GETSTATUS)
        self.mid_to_sockets[destination].send(msg)
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
