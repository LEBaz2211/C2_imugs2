class Buddy:
    def __init__(self, agent_id, localization = None, destination = None, nominal_speed = None, current_speed = None, max_speed = None):
        self.agent_id = agent_id
        self.localization = localization
        self.destination = destination
        self.current_speed = current_speed
        self.max_speed = max_speed
        self.nominal_speed = nominal_speed

    def __hash__(self):
        return hash(self.agent_id)

    def __eq__(self, other):
        if isinstance(other, Agent):
            return self.agent_id == other.agent_id
        return False
