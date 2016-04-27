import socket
import json
from enum import Enum

import thread
import sys
import random
import time
import os

from message import recv_msg, send_msg, decode_msg, create_msg, Action, PaxosMessenger

from paxos.practical import Messenger

from threading import Lock

class Agent(object):
    def __init__(self, value):
        self.value = value

    def __lt__(self, other):
        return self.value < other.value

    def __gt__(self, other):
        return self.value > other.value


'''
getstatus/sendstatus
test timeouts
ballot for starting migration -- check quorums
ballot for migration agents
'''

class IslandStatus(Enum):
    EVOLUTION = 0
    EVOLUTION_DONE = 1
    MIGRATION_READY = 2
    MIGRATION = 3
    IDLE = 4

class Island(object):
    def __init__(self, mid, my_agents, all_agents, mid_to_ports):
        '''
        Initializes a machine which represents an evolutionary island 
        
        :param mid: unique identifier for this machin
        :param my_agents: the agent IDs of all agents to be evolved by this machine
        :param all_agents: the agent IDs of all agents in the evolutionary population
                            (across all machines)
        :param mid_to_ports: tuple of (host, port) of machine with ID mid
        '''
        print 'Machine #%d: Initializing' % mid
        self.mid = mid
        self.my_agents = my_agents
        self.all_agents = all_agents 
        self.num_epochs = 1
        self.mid_to_sockets = {}
        self.status = IslandStatus.IDLE
        self.shuffled_agents = None

        self.socket_lock = Lock()
        self.ready_for_migration = False

        self.connect(mid_to_ports)

        # This island abides by the Paxos protocol
        self.paxos_messenger = PaxosMessenger(self.mid, self.mid_to_sockets) 
        self.paxos_proposer = Proposer()
        self.paxos_proposer.proposer_id = self.mid
        self.paxos_proposer.messenger = self.paxos_messenger
        self.paxos_proposer.quorum_size = len(self.mid_to_sockets)/2 + 1

        print 'Machine #%d: Done Initializing' % self.mid

        def die_thread():
            '''
            Causes this machine to die with some probability at any point
            This allows us to test machine failures.
            '''
            p = 0.05
            while True:
                time.sleep(1)
                if random.random() < p:
                    print 'Machine #%d: PANIC PANIC PANIC PANIC!!!' % self.mid
                    os._exit(1)

        thread.start_new_thread(die_thread, ())

    def get_status_handler(self, msg):
        '''
        Send the status of this island (alive, currently eovlving, ready to migrate, etc.
        to the indicated recipient

        :param receiver: The mid of the machine to which the status is sent
        :return: Success or failure of the send
        '''
        agents = []
        if self.status == IslandStatus.EVOLUTION_DONE:
            agents = [a.value for a in self.shuffled_agents]

        return create_msg(self.mid, Action.REPLYSTATUS, status=self.status.value, agents=agents)

    def get_all_agents(self):
        # at every migration, get all agents from live machines
        pass

    def run(self): 
        while(True):
            self.status = IslandStatus.EVOLUTION
            for _ in range(self.num_epochs):
                self.run_epoch()

            agents = self.my_agents[:]
            random.shuffle(agents)

            self.shuffled_agents = agents

            mid_to_agents = {self.mid: self.shuffled_agents}
            self.status = IslandStatus.EVOLUTION_DONE

            with self.socket_lock:
                mids = self.mid_to_sockets.keys()

            while self.status != IslandStatus.MIGRATION:
                numresponses = 0
                for mid in mids:
                    if mid != self.mid and mid not in mid_to_agents:
                        status, agents = self.get_status(mid)
                        if status is not None and agents:
                            self.mid_to_agents[mid] = agents
                        if status is not None:
                            numresponses += 1

                done = True
                with self.socket_lock:
                    for mid in self.mid_to_sockets:
                        if mid not mid_to_agents:
                            done = False
                            break
                    for mid in mid_to_agents:
                        if mid not in self.mid_to_sockets:
                            del mid_to_agents[mid]

                if done or numresponses == 0:
                    # Start Paxos Ballot to start migration
                    self.status = IslandStatus.MIGRATION_READY
                    self.paxos_proposer.set_proposal(mid_to_agents.keys())
                    self.paxos_proposer.prepare()

                    if not done:
                        self.status = IslandStatus.EVOLUTION_DONE

                time.sleep(4)


    def run_epoch(self):
        time.sleep(1.0 + random.randint(0, 100)/100.0)

    def run_migration(self):
        # permute list
        # send list to all participating migration islands
        time.sleep(1.0 + random.randint(0, 200)/100.0)

    def get_status(self, destination):
        '''
        Get the status of the destination island

        :param destination: The mid of the machine whose status to get
        :return: status of the machine 
        '''

        resp = self.rpc_call(destination, Action.GETSTATUS)
        if resp is not None:
            return IslandStatus(resp['status']), [Agent(i) for i in resp['agents']]
        return None, []

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

    def rpc_call(self, destination, action, *args, **kwargs):
        msg = create_msg(self.mid, action)
        print 'Machine #%d: Action %s sent to %d' % (self.mid, action.name, destination)
        try:
            socket = None
            with self.socket_lock:
                if destination in self.mid_to_sockets:
                    socket = self.mid_to_sockets[destination]

            send_msg(socket, msg)
            resp = recv_msg(socket)
            return decode_msg(resp)
        # except socket.timeout as e:
        #     with self.socket_lock:
        #         try:
        #             self.mid_to_sockets[destination].shutdown(socket.SHUT_RDWR)
        #             self.mid_to_sockets[destination].close()
        #         except Exception:
        #             pass
        #         del self.mid_to_sockets[destination]
        #         print 'Machine #%d: I think machine %d died' % (self.mid, destination)
        except RuntimeError as e:
            with self.socket_lock:
                try:
                    self.mid_to_sockets[destination].shutdown(socket.SHUT_RDWR)
                    self.mid_to_sockets[destination].close()
                except Exception:
                    pass
                del self.mid_to_sockets[destination]
                print 'Machine #%d: I think machine %d died' % (self.mid, destination)

        return None

    def connect(self, mid_to_ports):
        self.mid_to_sockets[self.mid] = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.mid_to_sockets[self.mid].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.mid_to_sockets[self.mid].bind(mid_to_ports[self.mid])
        # Become a server socket
        self.mid_to_sockets[self.mid].listen(5)
        self.mid_to_sockets[self.mid].settimeout(None)
        self.listen()
        print 'Machine #%d: Created server' % self.mid
        time.sleep(1.0)
        for mid in mid_to_ports:
            if mid != self.mid:
                self.mid_to_sockets[mid] = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                self.mid_to_sockets[mid].connect(mid_to_ports[mid])
                # Set a timeout for 1 second
                self.mid_to_sockets[mid].settimeout(1)

    def listen(self):
        def process(sock):
            try:
                while True:
                    msg = decode_msg(recv_msg(sock))
                    print 'Machine #%d: Received %s' % (self.mid, msg['action'].name)

                    response = {}
                    if msg['action'] == Action.GETSTATUS:
                        response = self.get_status_handler(msg)
                    else:
                        raise Exception('Unexpected message!!!!!')

                    # Force a timeout with probability 1% for testing purposes
                    if random.random() < 0.01:
                        # Oopsies network is slow
                        time.sleep(1.5)

                    send_msg(sock, response)

            except RuntimeError as e:
                pass

            try:
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()
            except Exception:
                pass

        def loop():
            while True:
                #accept connections from outside
                clientsocket, address = self.mid_to_sockets[self.mid].accept()
                ct = thread.start_new_thread(process, (clientsocket,))

        thread.start_new_thread(loop, ())


