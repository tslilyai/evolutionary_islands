import socket
import json
from enum import Enum

import thread
import sys
import random
import time
import inspect
import os

from message import recv_msg, send_msg, decode_msg, create_msg, Action, PaxosMessenger

from paxos.practical import Node, ProposalID
from threading import Lock

def mk_proposal_id(l):
    '''
    creates a proposal ID for a Paxos ballot to send

    :param l: proposal label (either None or a pair of 
              proposal_id, proposal_value)
    '''
    if l is None:
        return l
    return ProposalID(l[0], l[1])

class Agent(object):
    '''
    An Agent object is evolved by the Island.
    This class provides the interface that can be implemented
    for specific evolutionary algorithm agent representations (i.e.
    a Neural Network or a value)

    During evolution, an agent's genotype (i.e. agent ID and parameters)
    are passed around the islands. This is so that we can have several
    different agent representations/Agent subclasses that can all be
    evolved by an Island instantiation.

    However, an agent representation in the all_agents or my_agents lists is
    always an Agent type
    '''
    def __init__(self, genotype):
        ''' initialize the agent '''
        raise NotImplementedError

    def get_genotype(self):
        '''
        Returns the ID and genes of the agent (e.g. 
        agent ID and Neural net parameter weights,
        or agent ID and agent characteristics/value).
        '''
        raise NotImplementedError

class IslandStatus(Enum):
    '''
    IslandStatus defines the different states 
    in which an island can be in.
    '''
    EVOLUTION = 0
    EVOLUTION_DONE = 1
    MIGRATION_READY = 2
    MIGRATION = 3
    IDLE = 4

class Island(object):
    '''
    An Island object defines an evolutionary island that
    evolves a subset of the global agent population and
    participates in migrations
    '''

    def __init__(self, mid, my_agents, all_agents, mid_to_ports, AgentType):
        '''
        Initializes a machine which represents an evolutionary island 
        
        :param mid: unique identifier for this machin
        :param my_agents: the agent IDs of all agents to be evolved by this machine
        :param all_agents: the agent IDs of all agents in the evolutionary population
                            (across all machines)
        :param mid_to_ports: tuple of (host, port) of machine with ID mid
        '''
        self.mid = mid
        self.my_agents = my_agents
        self.all_agents = all_agents 
        self.num_epochs = 1
        self.mid_to_sockets = {}
        self.status = IslandStatus.IDLE
        self.migration_id = 0
        self.shuffled_agents = None
        self.AgentType = AgentType

        self.dprint('Initializing')

        self.socket_lock = Lock()
        self.status_lock = Lock()
        self.ready_for_migration = False
        self.migration_participants = []

        self.connect(mid_to_ports)

        # This island abides by the Paxos protocol
        self.paxos_messenger = PaxosMessenger(self.mid, self.mid_to_sockets, self) 
        self.paxos_node = Node(self.paxos_messenger, self.mid, len(self.mid_to_sockets)/2 + 1)

        self.dprint('Done Initializing')

        def die_thread():
            '''
            Causes this machine to die with some probability at any point
            This allows us to test machine failures.
            '''
            p = 0.05
            while True:
                time.sleep(1)
                if random.random() < p:
                    self.dprint('PANIC PANIC PANIC PANIC!!!')
                    os._exit(1)

        # thread.start_new_thread(die_thread, ())

    def create_msg(self, action, *args, **kwargs):
        '''
        create_message calls the internal message create_msg
        with an additional "migration_id" argument value.

        :param action: action of this message (message type, i.e. GETSTATUS)
        :param args: arguments to the message
        :param kwargs: additional (dict-type) arguments to the message
        :return: json-encoded message
        '''
        kwargs['migration_id'] = self.migration_id
        msg = create_msg(self.mid, action, *args, **kwargs)
        return msg

    def dprint(self, fmt, *args, **kwargs):
        colors = ['\033[32m', '\033[33m', '\033[34m', '\033[35m', '\033[36m', '\033[92m', '\033[93m', '\033[94m', '\033[95m', '\033[96m']
        _, fname, lineno, funcname, _, _ = inspect.getouterframes(inspect.currentframe())[1]
        fname = os.path.basename(fname)
        color = colors[self.mid % len(colors)] if 'critical' not in kwargs else '\033[31m'
        print (('%s%s [Machine %d, migration %d (%s)] [%s (%s:%d)]\033[00m ' %
                (color, time.strftime('%H:%M:%S'), self.mid, self.migration_id, self.status, funcname, fname, lineno))
               + (fmt % args))
        sys.stdout.flush()

    def prepare_migrate(self, migration_participants):
        '''
        set the status of the island to running migration

        :param migration_participants: participating islands in the migration
        :return: none
        '''
        self.migration_participants = migration_participants[:]
        with self.status_lock:
            if self.status != IslandStatus.MIGRATION:
                self.status = IslandStatus.MIGRATION

    '''
    MESSAGE HANDLERS
    
    Handlers of Paxos messages only respond when island status = MIGRATION_READY.
    The get_status handler responds at any point.
    '''
    def get_status_handler(self, msg):
        '''
        Send the status of this island (alive, currently eovlving, ready to migrate, etc.
        to the indicated recipient

        :param receiver: The mid of the machine to which the status is sent
        :return: Success or failure of the send
        '''
        agents = []

        with self.status_lock:
            if self.status == IslandStatus.EVOLUTION_DONE or self.status == IslandStatus.MIGRATION_READY:
                agents = [a.get_genotype() for a in self.shuffled_agents]

        return self.create_msg(Action.REPLYSTATUS, status=self.status.value, agents=agents)

    def prepare_handler(self, msg):
        '''
        prepare_handler only response to the prepare request if 
            1) the island is in the list of proposed islands and
            2) the island has heard back from all the proposed islands

        :param msg: accepted message sent, which includes the proposal id, the from uid, 
                    and the proposal value,
        :return: none
        '''
        kwargs = msg['kwargs']

        # if the island is not included in the list of participating islands,
        # the island cannot promise to participate...
        if self.mid not in kwargs['proposal_value']:
            self.dprint("prepare rejected")
            return
        self.dprint("mid is in proposal value")
        # if this island has not heard back from all islands in the proposed migration, 
        # it cannot promise to run the migration
        for island in kwargs['proposal_value']:
            if island not in self.mid_to_agents:
                self.dprint("%d not in mid_to_agents (%s)", island, self.mid_to_agents.keys())
                return

        self.paxos_node.recv_prepare(kwargs['from_uid'], mk_proposal_id(kwargs['proposal_id']), kwargs['proposal_value'])

    def accepted_handler(self, msg):
        '''
        accepted_handler handles messages saying that the accept request was accepted

        :param msg: accepted message sent, which includes the proposal id, the from uid, 
                    and the accepted value,
        :return: none
        '''
        kwargs = msg['kwargs']
        self.paxos_node.recv_accepted(kwargs['from_uid'], mk_proposal_id(kwargs['proposal_id']), kwargs['accepted_value'])
        if self.mid in kwargs['accepted_value']:
            self.prepare_migrate(kwargs['accepted_value'])

    def accept_handler(self, msg):
        '''
        accept_handler accepts the request 

        :param msg: accept message sent, which includes the proposal id, the from uid, 
                    and the proposal value,
        :return: none
        '''
        kwargs = msg['kwargs']
        self.paxos_node.recv_accept_request(kwargs['from_uid'], mk_proposal_id(kwargs['proposal_id']), kwargs['proposal_value'])
        if self.mid in kwargs['proposal_value']:
            self.prepare_migrate(kwargs['proposal_value'])

    def promise_handler(self, msg):
        '''
        promise_handler sends a promise to run this migration.

        :param msg: promise message sent, which includes the proposal id, the from uid, the previously
                    accepted proposal id, and the previously accepted value
        :return: none
        '''
        kwargs = msg['kwargs']

        self.dprint('%s', kwargs)
        self.dprint('quorum_size = %d', self.paxos_node.quorum_size)
        self.paxos_node.recv_promise(kwargs['from_uid'], mk_proposal_id(kwargs['proposal_id']), mk_proposal_id(kwargs['prev_accepted_id']),
                                     kwargs['prev_accepted_value'])

    def prepare_nack_handler(self, msg):
        '''
        prepare_nack_handler handles prepare_nack messages

        :param msg: prepare_nack message sent, which includes the proposal id, the from uid, and 
                    the promised_id
        :return: none
        '''
        kwargs = msg['kwargs']
        self.paxos_node.recv_prepare_nack(kwargs['from_uid'], mk_proposal_id(kwargs['proposal_id']), mk_proposal_id(kwargs['promised_id']))

    def accept_nack_handler(self, msg):
        '''
        accept_nack_handler handles accept_nack messages

        :param msg: accept_nack message sent, which includes the proposal id, the from uid, and 
                    the promised_id
        :return: none
        '''
        kwargs = msg['kwargs']
        self.paxos_node.recv_prepare_nack(kwargs['from_uid'], mk_proposal_id(kwargs['proposal_id']), mk_proposal_id(kwargs['promised_id']))

    def run(self): 
        '''
        Runs the island main loop (until the island crashes or is shut down).
        This loop does the following actions:
            1. run several epochs of evolution
            2. randomly shuffle the evolved agents in this machine's population
            3. while the machine is not participating in a migration:
                - poll for the status and evolved agents of every other machine
                - send a new_migration ballot, with the proposal including all machines
                    which will participate in this ballot

        Note that the listener thread may cause the machine to begin migration if
        1) the machine's ballot is proposed and accepted by a quorum, or 2) the 
        machine itself participates in another machine's proposed migration.
        '''
        while(True):
            with self.status_lock:
                self.status = IslandStatus.EVOLUTION
            for _ in range(self.num_epochs):
                self.run_epoch()

            agents = self.my_agents[:]
            random.shuffle(agents)

            self.shuffled_agents = agents

            self.mid_to_agents = {self.mid: self.shuffled_agents}
            with self.status_lock:
                self.status = IslandStatus.EVOLUTION_DONE

            with self.socket_lock:
                mids = self.mid_to_sockets.keys()

            while self.status != IslandStatus.MIGRATION:
                numresponses = 0
                for mid in mids:
                    if self.status == IslandStatus.MIGRATION:
                        break
                    if mid != self.mid and mid not in self.mid_to_agents:
                        status, agents = self.get_status(mid)
                        if status is not None and agents:
                            self.mid_to_agents[mid] = [self.AgentType(a) for a in agents]
                        if status is not None:
                            numresponses += 1

                done = True
                if self.status == IslandStatus.MIGRATION:
                    break

                with self.socket_lock:
                    # check to see if we've heard back from all islands
                    for mid in self.mid_to_sockets:
                        if mid not in self.mid_to_agents:
                            done = False
                            break
                    # check to see if an island has died in the time since we've
                    # heard from the island
                    mid_to_agents = self.mid_to_agents
                    for mid in mid_to_agents:
                        if mid not in self.mid_to_sockets:
                            del self.mid_to_agents[mid]


                if done or numresponses == 0:
                    self.dprint("Got everyone's status: %s", mid_to_agents.keys())
                    with self.status_lock:
                        if self.status == IslandStatus.MIGRATION:
                            break
                        self.status = IslandStatus.MIGRATION_READY
                    # Start Paxos Ballot to start migration
                    self.paxos_node.proposed_value = None
                    self.paxos_node.set_proposal(mid_to_agents.keys())
                    self.paxos_node.change_quorum_size(max(len(mid_to_agents.keys())-1, 
                                                            self.paxos_node.quorum_size))
                    self.dprint("Preparing proposal")
                    self.paxos_node.prepare()

                    time.sleep(2)

                    if self.status == IslandStatus.MIGRATION:
                        break

                time.sleep(4)
                with self.status_lock:
                    if self.status == IslandStatus.MIGRATION:
                        break
                    if not done:
                        self.dprint("Back to polling!")

            assert self.status == IslandStatus.MIGRATION
            # self.migration_participants is a list of islands that have ratified paxos proposal
            # since an island only accepts a proposal if it has heard back from all islands in the 
            # proposal, there should be no KeyErrors
            # all_agents should thus be in the same order for all machines participating in the
            # migration
            self.all_agents = []
            for key in self.migration_participants:
                self.all_agents += self.mid_to_agents[key] 
            self.run_migration()
            self.migration_id += 1

    def run_epoch(self):
        '''
        Function to run one epoch of evolution.
        Should be overridden to suit the purposes of whichever
        evolutionary algorithm is being run
        '''
        raise NotImplementedError

    def run_migration(self):
        '''
        Runs the migration process by assigning this island 
        every multiple of n agents plus the island's position in the migration
        participants list.
        n is the number of participating islands
        '''
        self.my_agents = []
        my_index = sorted(self.migration_participants).index(self.mid)
        num_participants = len(self.migration_participants)
        for i, agent in enumerate(self.all_agents):
            if (i-my_index) % num_participants == 0:
                self.my_agents.append(agent)

    def get_status(self, destination):
        '''
        Get the status of the destination island

        :param destination: The mid of the machine whose status to get
        :return: status of the machine and list of machine's agents (if the island
                    is done evolving)
        '''

        resp = self.rpc_call(destination, Action.GETSTATUS)
        if resp is not None:
            # return the AID and genotype of the Agent for the recipient island machine 
            # to store and potentially evolve
            return IslandStatus(resp['kwargs']['status']), resp['kwargs']['agents']
        return None, []

    def rpc_call(self, destination, action, *args, **kwargs):
        '''
        Sends (using the protocol specified in message.py) a message to
        the specified destination machine.

        If the send times out, the other machine is considered as having failed,
        and the socket to that machine closed.

        :param destination: MID to which to send the message
        :param action: action of this message (message type, i.e. GETSTATUS)
        :param args: arguments to the message
        :param kwargs: additional (dict-type) arguments to the message
        :return: decoded response to the message
        '''
        msg = self.create_msg(action)
        self.dprint('Action %s sent to %d', action.name, destination)
        try:
            sock = None
            with self.socket_lock:
                if destination in self.mid_to_sockets:
                    sock = self.mid_to_sockets[destination]

            send_msg(sock, msg)
            resp = recv_msg(sock)
            try:
                return decode_msg(resp)
            except ValueError as e:
                self.dprint(resp)
                raise e
        except socket.timeout:
            return None
        except RuntimeError as e:
            with self.socket_lock:
                try:
                    self.mid_to_sockets[destination].shutdown(socket.SHUT_RDWR)
                    self.mid_to_sockets[destination].close()
                except Exception:
                    pass
                del self.mid_to_sockets[destination]
                self.dprint('I think machine %d died' % destination)

        return None

    def connect(self, mid_to_ports):
        '''
        Sets up sockets and connects to all other machines.

        :param mid_to_ports: dictionary mapping a machine's ID to a (host, port) address
                             upon which the machine listens to requests
        :return: None
        '''
        self.mid_to_sockets[self.mid] = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.mid_to_sockets[self.mid].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.mid_to_sockets[self.mid].bind(mid_to_ports[self.mid])
        # Become a server socket
        self.mid_to_sockets[self.mid].listen(5)
        self.mid_to_sockets[self.mid].settimeout(None)
        self.listen()
        self.dprint('Created server')
        time.sleep(0.5)
        for mid in mid_to_ports:
            if mid != self.mid:
                self.mid_to_sockets[mid] = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                self.mid_to_sockets[mid].connect(mid_to_ports[mid])
                # Set a timeout for 2 seconds
                self.mid_to_sockets[mid].settimeout(2)

    def listen(self):
        '''
        loop() sets up the listening socket from other machines

        process() listens for incoming requests from other machines and 
        handles msgs accordingly by passing them to their corresponding handlers.
        '''
        def process(sock):
            try:
                while True:
                    try:
                        mm = recv_msg(sock)
                        msg = decode_msg(mm)
                    except Exception as e:
                        self.dprint('ValueError: %s', mm, critical=True)
                        raise e
                    self.dprint('Received %s', msg['action'].name)

                    if msg['kwargs']['migration_id'] != self.migration_id:
                        self.dprint('Migration id mismatch (%d != %d), ignoring message %s', msg['kwargs']['migration_id'], self.migration_id, msg)
                        continue

                    response = {}
                    if msg['action'] == Action.GETSTATUS:
                        response = self.get_status_handler(msg)
                    elif self.status == IslandStatus.MIGRATION_READY:
                        if msg['action'] == Action.SEND_PREPARE_NACK:
                            response = self.prepare_nack_handler(msg)
                        elif msg['action'] == Action.SEND_ACCEPT_NACK:
                            response = self.accept_nack_handler(msg)
                        elif msg['action'] == Action.SEND_PREPARE:
                            response = self.prepare_handler(msg)
                        elif msg['action'] == Action.SEND_PROMISE:
                            response = self.promise_handler(msg)
                        elif msg['action'] == Action.SEND_ACCEPT:
                            response = self.accept_handler(msg)
                        elif msg['action'] == Action.SEND_ACCEPTED:
                            response = self.accepted_handler(msg)
                    else:
                        self.dprint('Cannot handle message')
                    
                    # Force a timeout with probability 1% for testing purposes
                    if random.random() < 0.01:
                        # Oopsies network is slow
                        time.sleep(1.5)
                    
                    if response:
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
