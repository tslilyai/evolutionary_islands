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
    SENDSTATUS = 1
    '''
    TODO
    SEND_START_MIGRATION = 2
    ACCEPT_START_MIGRATION = 3
    '''

class MsgLen():
    GETSTATUS = 1#size here
    SENDSTATUS = 0#size here
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

def send_msg(msg, dest):
    '''
    :param msg: string msg to send to the recipient
    :param dest: destination socket 
    :return: message (string)
    '''
    msg_len = len(msg)
    totalsent = 0
    while totalsent < msg_len:
        sent = dest.send(msg[totalsent:])
        if sent == 0:
            raise RuntimeError("socket connection broken")
        totalsent += sent

def recv_msg(msg_len):
    '''
    :param msg_len: MsgLen object that tells how long the received msg should be
    :return: message (string)
    '''
    chunks = []
    bytes_recd = 0
    while bytes_recd < MSGLEN:
        chunk = self.sock.recv(min(MSGLEN - bytes_recd, 2048))
        if chunk == '':
            raise RuntimeError("socket connection broken")
        chunks.append(chunk)
        bytes_recd = bytes_recd + len(chunk)
    return ''.join(chunks)
