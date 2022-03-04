import utils.globals as GG


class Question:
    def __init__(self, position: int, text: str, placeholder: str, style: int, required: bool):
        self.position = position
        self.text = text
        self.placeholder = placeholder
        self.style = style
        self.required = required

    @classmethod
    async def new(cls, position, text, placeholder, style, required):
        inst = cls(position, text, placeholder, style, required)
        return inst

    @classmethod
    def from_dict(cls, question_dict):
        return cls(**question_dict)

    def to_dict(self):
        return {"position": self.position, "text": self.text, "placeholder": self.placeholder, "style": self.style, "required": self.required}


class Questionaire:
    collection = GG.MDB['questions']

    def __init__(self, server: int, identifier: str, questions: list = None):
        if questions is None:
            questions = []
        self.server = server
        self.identifier = identifier
        self.questions = questions

    @classmethod
    async def new(cls, server, identifier):
        inst = cls(server, identifier, questions=None)
        return inst

    @classmethod
    def from_dict(cls, questionaire_dict):
        return cls(**questionaire_dict)

    def to_dict(self):
        return {"server": self.server, "identifier": self.identifier, "questions": self.questions}

    @classmethod
    async def from_id(cls, identifier, server):
        questionaire = await cls.collection.find_one({"identifier": identifier, "server": server})
        if questionaire is not None:
            del questionaire['_id']
            return cls.from_dict(questionaire)
        else:
            return None

    async def add_question(self, question: Question, confirmation=False):
        if confirmation is False:
            for q in self.questions:
                if question.position == q['position']:
                    return False
        else:
            for q in self.questions:
                if question.position == q['position']:
                    self.questions.remove(q)

        self.questions.append(question.to_dict())
        await self.commit()

    async def remove_question(self):
        pass

    async def commit(self):
        await self.collection.replace_one({"server": self.server, "identifier": self.identifier}, self.to_dict(), upsert=True)

