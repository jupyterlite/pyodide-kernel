class __named_commands__:
    def __getattr__(self, name):
        return name


named_commands = __named_commands__()
