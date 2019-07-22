class ContextProxy:  # just to pass the bot on to functions that need it
    def __init__(self, bot):
        self.bot = bot