import copy

from log import logger

class State:
    def __init__(self , stack , additional = None , command = None):
        self._stack = copy.deepcopy(stack)
        self._additional = additional
        self._command = command
        logger.debug(str(self))

    def get_stack(self):
        return copy.deepcopy(self._stack)

    def get_additional(self):
        return self._additional
    
    def get_top(self):
        if len(self._stack) > 0:
            return copy.deepcopy(self._stack[-1])
        else:
            return None

    def get_command(self):
        return copy.deepcopy(self._command)

    def add_to_program(self , element): # state -> state
        stack = self.get_stack()
        stack.append(element)
        additional = None

        return State(stack , additional , command = copy.deepcopy(element))

    def nicestr(self , width = 1000):
        a = "        "
        if self._additional is not None and "frames" in self._additional:
            a = "(" + format(len(self._additional['frames']) , '5d') + ") "
        r = " ".join(self._stack)
        if len(r) > width - 28:
            return a + "... " + r[-(width - 28):]
        else:
            return a + r
    
    def __str__(self):
        des = []
        des.append("stack : " + " ".join(self._stack))
        if self._additional is not None:
            des.append("additional elements : " + str(len(self._additional)))
        if self._command is not None:
            des.append("with command : "  + self._command)

        return "State(" + " , ".join(des) + ")"

    def __getstate__(self):
        return (self._stack , self._additional , self._command)

    def __setstate__(self , state):
        self._stack , self._additional , self._command = state


