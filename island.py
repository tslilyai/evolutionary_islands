import socket
import json
from enum import Enum

import thread
import sys
import random
import time
import os

from message import recv_msg, send_msg, decode_msg, create_msg, Action

'''
getstatus/sendstatus
test timeouts
ballot for starting migration -- check quorums
ballot for migration agents
'''

class Island(object):
    def __init__(self, mid, my_agents, all_agents, mid_to_ports):
        '''
        :param mid_to_ports: tuple of (host, port) of machine with ID mid
        '''
        print 'Machine #%d: Initializing' % mid
        self.mid = mid
        self.my_agents = my_agents
        self.all_agents = all_agents 
        self.num_epochs = 1
        self.mid_to_sockets = {}


        self.mid_to_sockets[self.mid] = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.mid_to_sockets[self.mid].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.mid_to_sockets[self.mid].bind(mid_to_ports[self.mid])
        #become a server socket
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
                self.mid_to_sockets[mid].settimeout(None)

        print 'Machine #%d: Done Initializing' % self.mid


        def die_thread():
            '''Randomly dies with some probability
            '''
            p = 0.05
            while True:
                time.sleep(1)
                if random.random() < p:
                    print 'Machine #%d: PANIC PANIC PANIC PANIC!!!' % self.mid
                    os._exit(1)

        thread.start_new_thread(die_thread, ())


    def listen(self):
        def process(sock):
            try:
                while True:
                    msg = decode_msg(recv_msg(sock))

                    if msg['action'] == Action.GETSTATUS:
                        print 'Machine #%d: Received GETSTATUS' % (self.mid)
                        send_msg(sock, create_msg(self.mid, Action.REPLYSTATUS, 0))
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

    def get_all_agents(self):
        # at every migration, get all agents from live machines
        pass

    def run(self): 
        while(True):
            for _ in range(self.num_epochs):
                self.run_epoch()

            mids = self.mid_to_sockets.keys()
            for mid in mids:
                if mid != self.mid:
                    status = self.get_status(mid)

    def run_epoch(self):
        time.sleep(1.0 + random.randint(0, 100)/100.0)

    def run_migration(self):
        # permute list
        # send list to all participating migration islands
        time.sleep(1.0 + random.randint(0, 200)/100.0)

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

        print 'Machine #%d: GETSTATUS of %d' % (self.mid, destination)
        msg = create_msg(self.mid, Action.GETSTATUS)
        try:
            if destination in self.mid_to_sockets:
                send_msg(self.mid_to_sockets[destination], msg)
                resp = recv_msg(self.mid_to_sockets[destination])
        except socket.timeout as e:
            try:
                self.mid_to_sockets[destination].shutdown(socket.SHUT_RDWR)
                self.mid_to_sockets[destination].close()
            except Exception:
                pass
            del self.mid_to_sockets[destination]
            print 'Machine #%d: I think machine %d died' % (self.mid, destination)
        except RuntimeError as e:
            try:
                self.mid_to_sockets[destination].shutdown(socket.SHUT_RDWR)
                self.mid_to_sockets[destination].close()
            except Exception:
                pass
            del self.mid_to_sockets[destination]
            print 'Machine #%d: I think machine %d died' % (self.mid, destination)

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
