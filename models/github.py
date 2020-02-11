class Listen:
    def __init__(self, id: int, identifier: str, repo: str):
        self.id = id
        self.identifier = identifier
        self.repo = repo

    @classmethod
    def from_data(cls, data):
        return cls(data['id'], data['identifier'], data['repo'])

class Github:
    def __init__(self, name: str, server: int, admin: int, tracker: int, org: str, listen: []):
        self.name = name
        self.server = server
        self.admin = admin
        self.tracker = tracker
        self.org = org
        self.listen = listen

    @classmethod
    def from_data(cls, data):
        listen = []
        listeners = data['listen']
        for x in listeners:
            listen.append(Listen.from_data(x))
        return cls(data['name'], data['server'], data['admin'], data['tracker'], data['org'], listen)
