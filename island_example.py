import os
import socket
import random
import time

from island import Agent, Island

class ValueAgent(Agent):
    '''
    ValueAgent provides a dummy example of what an agent may be.
    This agent's value is equivalent to its agent ID.
    '''
    def __init__(self, value):
        self.value = value

    def __lt__(self, other):
        return self.value < other.value

    def __gt__(self, other):
        return self.value > other.value

    def get_genotype(self):
        return self.value

class ValueIsland(Island):
    '''
    Example island class to evolve ValueAgents
    '''

    def run_epoch(self):
        '''
        Function to run one epoch of evolution.
        Can be overridden to suit the purposes of whichever
        evolutionary algorithm is being run
        '''
        time.sleep(1.0 + random.randint(0, 100)/100.0)

def main():
    hostname = 'localhost'
    mid_to_ports = {
        1: (hostname, 6011),
        2: (hostname, 6012),
        3: (hostname, 6013),
        4: (hostname, 6014),
    }

    pid1 = os.fork()
    pid2 = os.fork()

    agents = [ValueAgent(i) for i in range(100)]

    if pid1 == 0 and pid2 == 0:
        isl = ValueIsland(1, agents[::4], agents, mid_to_ports)
    elif pid1 == 0:
        isl = ValueIsland(2, agents[1::4], agents, mid_to_ports)
    elif pid2 == 0:
        isl = ValueIsland(3, agents[2::4], agents, mid_to_ports)
    else:
        isl = ValueIsland(4, agents[3::4], agents, mid_to_ports)

    s = os.urandom(4)
    s = sum([256**i * ord(c) for i, c in enumerate(s)])
    random.seed(s)

    isl.run()


if __name__ == "__main__":
    main()

