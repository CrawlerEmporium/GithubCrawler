class Attachment:
    def __init__(self, author, message: str = '', veri: int = 0):
        self.author = author
        self.message = message or None
        self.veri = veri

    @classmethod
    def from_dict(cls, attachment):
        return cls(**attachment)

    def to_dict(self):
        return {"author": self.author, "message": self.message, "veri": self.veri}

    @classmethod
    def upvote(cls, author, msg=''):
        return cls(author, msg, 2)

    @classmethod
    def downvote(cls, author, msg=''):
        return cls(author, msg, -2)

    @classmethod
    def indifferent(cls, author, msg=''):
        return cls(author, msg, 3)

    @classmethod
    def cr(cls, author, msg=''):
        return cls(author, msg, 1)

    @classmethod
    def cnr(cls, author, msg=''):
        return cls(author, msg, -1)