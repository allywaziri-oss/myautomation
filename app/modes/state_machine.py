class StateMachine:
    """Manage the application state."""

    STATES = ['IDLE', 'RECEIVE_ARMED', 'SEND_ARMED', 'CONNECTING', 'TRANSFERRING']

    def __init__(self):
        self.state = 'IDLE'

    def set_state(self, state):
        if state in self.STATES:
            self.state = state

    def get_state(self):
        return self.state