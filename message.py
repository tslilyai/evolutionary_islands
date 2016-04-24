from enum import Enum
import struct
import json
import sys
'''
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
    REPLYSTATUS = 1
    '''
    TODO
    SEND_START_MIGRATION = 2
    ACCEPT_START_MIGRATION = 3
    '''

def create_msg(mid, action, *args, **kwargs):
    return json.dumps({
        'mid': mid,
        'version': 0,
        'action': action.value,
        'args': args,
        'kwargs': kwargs
    })
    
def decode_msg(msg):
    ret = json.loads(msg)
    ret['action'] = Action(ret['action'])
    return ret

def send_msg(socket, msg):
    '''
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
    :param socket: socket from which to receive
    :return: message (string)
    '''
    m = ''
    m_len = 0
    while m_len < 4:
        chunk = socket.recv(2048)
        if chunk == '':
            raise RuntimeError('Socket connection error')
        m += chunk
        m_len += len(chunk)

    msg_len, = struct.unpack('<L', m[:4])

    chunks = []
    chunks.append(m[4:])
    bytes_recd = len(m[4:])
    while bytes_recd < msg_len:
        chunk = socket.recv(2048)
        if chunk == '':
            raise RuntimeError("socket connection broken")
        chunks.append(chunk)
        bytes_recd = bytes_recd + len(chunk)
    return ''.join(chunks)
