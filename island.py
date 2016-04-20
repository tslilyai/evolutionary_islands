
class Island(object):
    def __init__(mid, my_agents, all_agents):
        self.mid = mid
        self.my_agents = my_agents
        self.agents = agents 
        # TODO set up sockets here

    def get_all_agents(self):
        # XXX do we just get agents from everyone's db? 
        # what about agents that are dead? (we just send the entire database over?)
        pass

    def run_epoch(self):
        pass

    def run_migration(self):
        # permute list
        # send list to all participating migration islands
        pass

    def send_status(self, receiver):
        '''
        send the status of this island (alive, currently eovlving, ready to migrate, etc.
        to the indicated recipient
        '''
        pass

    def get_status(self, destination):
        '''
        get the status of the destination island
        '''
        pass
