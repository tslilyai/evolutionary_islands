import island

import os
import socket
import random

hostname = 'localhost'
mid_to_ports = {
    1: (hostname, 6011),
    2: (hostname, 6012),
    3: (hostname, 6013),
    4: (hostname, 6014),
}

pid1 = os.fork()
pid2 = os.fork()

agents = [island.Agent(i) for i in range(100)]

if pid1 == 0 and pid2 == 0:
    isl = island.Island(1, agents[::4], agents, mid_to_ports)
elif pid1 == 0:
    isl = island.Island(2, agents[1::4], agents, mid_to_ports)
elif pid2 == 0:
    isl = island.Island(3, agents[2::4], agents, mid_to_ports)
else:
    isl = island.Island(4, agents[3::4], agents, mid_to_ports)

s = os.urandom(4)
s = sum([256**i * ord(c) for i, c in enumerate(s)])
random.seed(s)

isl.run()
