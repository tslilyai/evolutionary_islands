# Evolutionary Islands
CS262 Final Project: Distributed System for Evolutionary Island Algorithms

Lily Tsai and David Ding

Evolutionary Islands is a distributed system framework for evolutionary island algorithms. 
In our project, we propose a distributed system algorithm with the goals of making agent distribution completely self-organized by the machines in the cluster (with any machine capable of being a leader), and robust to the failure of any one island. We utilize a variant of Paxos to implement our consensus algorithm, and modify the Paxos implemention from https://github.com/cocagne/paxos.

##Usage
Our code is general to any type of evolutionary algorithm that evolves a set of agents with a specific representation. To use our system, one should implement the Agent class and the Island class. An example of this can be found in `island_example.py`.

To run the evolution, run `python island_example.py [--num_epochs 100] [--test_failures True]`, replacing the file name with your own specific instantiations of the Island and Agents classes. 

If test_failures is set to True, then an island will randomly die with some probability at any time to test machine crashes/failures. In addition, it will force a timeout during message responses with some random probability to test what happens should the network connection be slow.

When the system is run, each machine prints out messages (color-coded per machine) that describe the messages the machine is receiving or sending, and the migration status of the machine (including its migration ID).

###Island Class
Any class that inherits from Island must override the `run_epoch` function, which takes no arguments and simply runs one epoch of the evolutionary algorithm (for example, mutating and evolving the set of agents belonging to that island).

##Agent Class
Any class that implements the Agent class should implement the following interface, which is likely to interact with the island class' specific implementation of `run_epoch`.
```
    def __init__(self, genotype):
        ''' initialize the agent '''

    def get_genotype(self):
        '''
        Returns the ID and genes of the agent (e.g. 
        agent ID and Neural net parameter weights,
        or agent ID and agent characteristics/value).
        '''
```

##System Design
The system model consists of a distributed cluster of centralized server clusters. There are three levels of machines we deal with:
    1. Cluster of machines, each representing an island of evolution
    2. Island machines that act as centralized servers for evolving their agent population 
    3. Agent simulation servers that respond to and talk with the island machines
For our project, we assume that we can consider each island of evolution as an integrated unit;
in particular, we do not consider communications within an island. We therefore assume that each island is a single machine.

###Migration Model
    *Immigration Policy:*
 Agents will be chosen at random to migrate.
    
    *Migration Frequency:* Agents will migrate every E epochs, where each epoch consists of an evolution of the subpopulations with in each island. This parameter E defaults to 100 and can be configured by passing TODO
    
    *Migration Density:* 
Each migration, every agent in each subpopulation will be sent to an island at random (which could be its current home island).
    
    *Migrant Topology:* Migrants are distributed as follows:
        - Each machine is associated with a unique machine ID (mid).
        - During a migration, each machine sends to every other machine its ID and a list of its agents shuffled in a random order.
        - Once all the machines receive all lists, they select the nth subset of agents from each list to be the new agents on their island, where n is the position of the machine in a list of sorted mids.

###Island State Machine

An island transitions through the following states within its lifetime:
    1. *Evolving:* The island is currently running its $E$ epochs of evolution. During this time, the island ignores any migration proposals and does not interact with any other machines.
    2. *Evolution Done:* The island has finished evolving its agents and is ready to migrate. During this time, the island queries all other island for their status to get an initial list of machines to include in its migration proposal. Once these queries have either received responses or have timed out, the island transitions to the ``Start Migration'' phase. Should the island receive any queries from other islands, the island will send out a list of its agents in a randomly shuffled order along with its status.
    3. *Start Migration:* The island has proposed a migration ballot, and is also available to accept other migration ballots if allowed to do so under our modified Paxos protocol. If it has not accepted a migration proposal or its proposal has not been accepted after a time limit (currently set to 4 seconds), the island will re-query all machines again to generate a new migration ballot proposal.
    4. Should the island receive any queries from other islands, the island will send out a list of its agents in a randomly shuffled order along with its status.
    5. *Migrating:* During this phase, an island uses the shuffled list of agents from each island it has received from the status queries of the other islands to select its agents for the next round. This step is done locally and requires no interaction with any other islands. When in this state, the island ignores any migration proposals and does not send anything other than its status in response to a status request. Once migration has finished, the machine increments a Migration ID and returns to the evolution phase.
