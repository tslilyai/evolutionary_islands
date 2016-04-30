import os
import socket
import random
import time
import itertools
from collections import defaultdict

from island import Agent, Island

class FishAgent(Agent):
    '''
    ValueAgent provides a dummy example of what an agent may be.
    This agent's value is equivalent to its agent ID.
    '''
    def __init__(self, (fish_id, size)):
        self.size = size
        self.id = fish_id

    def get_genotype(self):
        return (self.id, self.size)

    def __can_swim_away__(self, other):
        '''
        a fish can swim away from another fish
        if its size is less than or equal to
        the other fish's size
        '''
        return self.size <= other.size

    def __can_eat__(self, other):
        '''
        a fish can eat another fish
        if its size is greater than the other
        fish's size.
        '''
        return self.size > other.size

class FishIsland(Island):
    '''
    Example island class to evolve FishAgents
    '''

    def run_epoch(self):
        scores = defaultdict(int)
        fish_combos = list(itertools.combinations(self.my_agents, 2))
        for (f1, f2) in fish_combos:
            if f1.__can_swim_away__(f2):
                scores[f1] += 1
            else:
                assert(not f2.__can_eat__(f1))
                scores[f2] += 1
        
        # mutate by multiplying sizes of the fish by its score, and randomly sometimes
        # dividing by the score
        new_agents = []
        for fish in self.my_agents:
            if random.random() < 0.2:
                new_agents.append(FishAgent((fish.id, float(fish.size)/1+scores[fish])))
            else:
                new_agents.append(FishAgent((fish.id, float(fish.size)*scores[fish])))

def main():
    hostname = 'localhost'
    mid_to_ports = {
        1: (hostname, 6011),
        2: (hostname, 6012),
        3: (hostname, 6013),
        4: (hostname, 6014),
        5: (hostname, 6015),
        6: (hostname, 6016),
        7: (hostname, 6017),
        8: (hostname, 6018),
    }

    pid1 = os.fork()
    pid2 = os.fork()
    pid3 = os.fork()

    agents = [FishAgent((i, i)) for i in range(104)]

    if pid1 == 0 and pid2 == 0 and pid3 == 0:
        isl = FishIsland(1, agents[::4], agents, mid_to_ports, FishAgent)
    elif pid1 == 0 and pid2 == 0:
        isl = FishIsland(2, agents[1::4], agents, mid_to_ports, FishAgent)
    elif pid1 == 0 and pid3 == 0:
        isl = FishIsland(3, agents[1::4], agents, mid_to_ports, FishAgent)
    elif pid2 == 0 and pid3 == 0:
        isl = FishIsland(4, agents[2::4], agents, mid_to_ports, FishAgent)
    elif pid1 == 0:
        isl = FishIsland(5, agents[2::4], agents, mid_to_ports, FishAgent)
    elif pid2 == 0:
        isl = FishIsland(6, agents[2::4], agents, mid_to_ports, FishAgent)
    elif pid3 == 0:
        isl = FishIsland(7, agents[2::4], agents, mid_to_ports, FishAgent)
    else:
        isl = FishIsland(8, agents[3::4], agents, mid_to_ports, FishAgent)

    s = os.urandom(4)
    s = sum([256**i * ord(c) for i, c in enumerate(s)])
    random.seed(s)

    isl.run()


if __name__ == "__main__":
    main()

