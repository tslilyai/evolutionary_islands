from enum import Enum
import struct
import json
import sys

from paxos.practical import Messenger

'''
message.py implements the message-sending protocol and functionality of our system.

The protocol encodes all messages as JSON with the following structure:
        mid: sender
        protocol version:
        action:
        args:
        kwargs:

Also included in this file is the definition of the PaxosMessenger class,
which allows machines to send ballots and reach consensus.
'''

class Action(Enum):
    ''' 
    Action specifies the type of messages/actions a machine
    is allowed to send.
    '''
    GETSTATUS = 0
    REPLYSTATUS = 1
    # Paxos actions
    SEND_PREPARE_NACK = 2
    SEND_ACCEPT_NACK = 3
    SEND_PREPARE = 4
    SEND_PROMISE = 5
    SEND_ACCEPT = 6
    SEND_ACCEPTED = 7

def create_msg(mid, action, *args, **kwargs):
    '''
    Returns a json-encoded message object that follows
    the protocol specified above.

    :param mid: MID to which to send the message
    :param action: action of this message (message type, i.e. GETSTATUS)
    :param args: arguments to the message
    :param kwargs: additional (dict-type) arguments to the message
    :return: json-encoded message
    '''
    return json.dumps({
        'mid': mid,
        'version': 0,
        'action': action.value,
        'args': args,
        'kwargs': kwargs
    })
    
def decode_msg(msg):
    '''
    Decodes a json-encoded message that follows the 
    protocol specified above

    :param msg: json-encoded message string
    :return: json-decoded message
    '''
    ret = json.loads(msg)
    ret['action'] = Action(ret['action'])
    return ret

def send_msg(socket, msg):
    '''
    Sends a message to the destination socket.

    :param socket: destination socket 
    :param msg: string msg to send to the recipient
    :return: message (string)
    '''
    msg = struct.pack('<L', len(msg)) + msg
    msg_len = len(msg)
    totalsent = 0
    while totalsent < msg_len:
        sent = socket.send(msg[totalsent:])
        if sent == 0:
            raise RuntimeError("socket connection broken")
        totalsent += sent

def recv_msg(socket):
    '''
    Recieves a message from the sending socket

    :param socket: socket from which to receive
    :return: message (string)
    '''
    m = ''
    m_len = 0
    while m_len < 4:
        chunk = socket.recv(4)
        if chunk == '':
            raise RuntimeError('Socket connection error')
        m += chunk
        m_len += len(chunk)

    msg_len, = struct.unpack('<L', m[:4])

    chunks = []
    chunks.append(m[4:])
    bytes_recd = len(m[4:])
    while bytes_recd < msg_len:
        chunk = socket.recv(msg_len - bytes_recd)
        if chunk == '':
            raise RuntimeError("socket connection broken")
        chunks.append(chunk)
        bytes_recd = bytes_recd + len(chunk)
    tot = ''.join(chunks)
    return tot

class PaxosMessenger(Messenger):
    def __init__(self, mid, mid_to_sockets, island):
        self.mid = mid
        self.mid_to_sockets = mid_to_sockets
        self.island = island

    def send_prepare_nack(self, to_uid, proposal_id, promised_id):
        self.island.rpc_call(to_uid, Action.SEND_PREPARE_NACK, from_uid=self.mid, to_uid=to_uid, proposal_id=proposal_id, promised_id=promised_id)

    def send_accept_nack(self, to_uid, proposal_id, promised_id):
        self.island.rpc_call(to_uid, Action.SEND_ACCEPT_NACK, from_uid=self.mid, to_uid=to_uid, proposal_id=proposal_id, promised_id=promised_id)

    def send_prepare(self, proposal_id, proposal_value):

        self.island.dprint("Preparing proposal: %s %s", proposal_id, proposal_value)
        mid_to_sockets = self.island.mid_to_sockets.keys()
        for to_uid in mid_to_sockets:
            if to_uid != self.mid:
                self.island.rpc_call(to_uid, Action.SEND_PREPARE, from_uid=self.mid, proposal_id=proposal_id, proposal_value=proposal_value)

    def send_promise(self, proposal_uid, proposal_id, previous_id, accepted_value):
        self.island.rpc_call(proposal_uid, Action.SEND_PROMISE, from_uid=self.mid, proposal_id=proposal_id, prev_accepted_id=previous_id, prev_accepted_value=accepted_value)


    def send_accept(self, proposal_id, proposal_value):
        self.island.dprint('Accept sent')
        for to_uid in self.island.mid_to_sockets:
            if to_uid != self.mid:
                self.island.rpc_call(to_uid, Action.SEND_ACCEPT, from_uid=self.mid, proposal_id=proposal_id, proposal_value=proposal_value)

    def send_accepted(self, proposal_id, accepted_value):
        for to_uid in self.island.mid_to_sockets:
            if to_uid != self.mid:
                self.island.rpc_call(to_uid, Action.SEND_ACCEPTED, from_uid=self.mid, proposal_id=proposal_id, accepted_value=accepted_value)

        self.island.paxos_node.recv_accepted(self.mid, proposal_id, accepted_value)

    def on_resolution(self, proposal_id, proposal_value):
        self.island.dprint('On resolution: %s, %s', proposal_id, proposal_value)
        if self.mid in proposal_value:
            self.island.prepare_migrate(proposal_value)
