class Listen:
    def __init__(self, channel: int, tracker: int, identifier: str, type: str, repo: str = "", url: str = "",
                 alias: str = ""):
        self.channel = channel
        self.tracker = tracker
        self.identifier = identifier
        self.type = type
        self.repo = repo
        self.url = url
        self.alias = alias

    @classmethod
    def from_data(cls, data):
        return cls(data['channel'], data['tracker'], data['identifier'], data['type'], data.get('repo', None),
                   data.get('url', None), data.get('alias', None))

    def to_dict(self):
        return {
            'channel': self.channel, 'tracker': self.tracker, 'identifier': self.identifier, 'type': self.type,
            'repo': self.repo, 'url': self.url, 'alias': self.alias
        }


class Server:
    def __init__(self, name: str, server: int, admin: int, org: str = None, listen=None, threshold: int = 5):
        if listen is None:
            listen = []
        self.name = name
        self.server = server
        self.admin = admin
        self.org = org
        self.listen = listen
        self.threshold = threshold

    @classmethod
    def from_data(cls, data):
        listen = []
        listeners = data['listen']
        for x in listeners:
            listen.append(Listen.from_data(x))
        return cls(data['name'], data['server'], data['admin'], data['org'], listen, data['threshold'])

    def to_dict(self):
        return {
            'name': self.name, 'server': self.server, 'admin': self.admin, 'org': self.org, 'listen': self.listen,
            'threshold': self.threshold
        }
