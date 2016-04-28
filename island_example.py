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

class ValueIsland(object):
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
