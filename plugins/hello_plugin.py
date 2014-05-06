import cliapp

class Hello(cliapp.Plugin):
    def __init__(self):
        self.nom = "Hello"

    def enable(self):
        self.app.add_subcommand("test", self.cmd_test)

    def cmd_test(self, args):
        print "Test!"
