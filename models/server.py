class Listen:
    def __init__(self, channel: int, tracker: int, identifier: str, repo: str):
        self.channel = channel
        self.tracker = tracker
        self.identifier = identifier
        self.repo = repo

    @classmethod
    def from_data(cls, data):
        return cls(data['channel'], data['tracker'], data['identifier'], data.get('repo', None))


class Server:
    def __init__(self, name: str, server: int, admin: int, org: str, listen: []):
        self.name = name
        self.server = server
        self.admin = admin
        self.org = org
        self.listen = listen

    @classmethod
    def from_data(cls, data):
        listen = []
        listeners = data['listen']
        for x in listeners:
            listen.append(Listen.from_data(x))
        return cls(data['name'], data['server'], data['admin'], data['org'], listen)
