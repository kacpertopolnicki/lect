import copy

from log import logger

import pickle
import zlib

class State:
    def __init__(self , stack , additional = None , command = None):
        self._stack = copy.deepcopy(stack)
        if additional is not None:
            # sauce : https://stackoverflow.com/questions/19500530/compress-python-object-in-memory
            self._additional = zlib.compress(pickle.dumps(additional))
        else:
            self._additional = None
        self._command = command
        logger.debug(str(self))

    def get_stack(self):
        return copy.deepcopy(self._stack)

    def get_additional(self):
        if self._additional is not None:
            return pickle.loads(zlib.decompress(self._additional))
        else:
            return None
    
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
        if self._additional is not None:
            a = " @      "
        #if self._additional is not None and "frames" in self._additional:
        #    a = " (v)    "
        #if self._additional is not None and "recording" in self._additional:
        #    a = " (a)    "
        #if self._additional is not None and "frames" in self._additional and "recording" in self._additional:
        #    a = " (va)   "
        
        def same_el(s1 , s2):
            if s1[1:2] == s2[1:2] == "_" and s1[:1] == s2[:1]:
                if int(s1[2:]) + 1 == int(s2[2:]):
                    return True
                if int(s1[2:]) == int(s2[2:]) + 1:
                    return True
                return False
            return False

        new_stack = copy.deepcopy(self._stack)
        if self._command is not None:
            if new_stack[-1] == self._command:
                new_stack[-1] = '[' + new_stack[-1] + ']'

        logger.debug(str(new_stack))

        starts = [0]
        for i in range(1 , len(new_stack)):
            if not same_el(new_stack[i] , new_stack[i - 1]):
                starts.append(i)

        logger.debug(str(starts))

        beginend = []
        for i in range(len(starts) - 1):
            beginend.append(new_stack[starts[i] : starts[i + 1]])
        beginend.append(new_stack[starts[-1] : len(new_stack)])

        rep = []
        for be in beginend:
            if len(be) > 0:
                if len(be) == 1:
                    rep.append(be[0])
                else:
                    rep.append(be[0] + "-" + be[-1])

        new_stack = copy.deepcopy(self._stack)
        if self._command is not None:
            new_stack = list(map(lambda x : '[' + x + ']' if x == self._command else x , new_stack))

        r = " ".join(rep)
        if len(r) > width - 4 - 8:
            return a + "... " + r[-(width - 4 - 8):]
        else:
            return a + r
    
    def __str__(self):
        des = []
        des.append("stack : " + " ".join(self._stack))
        if self._additional is not None:
            des.append("contains additional elements")
        if self._command is not None:
            des.append("with command : "  + self._command)

        return "State(" + " , ".join(des) + ")"

    def __getstate__(self):
        return (self._stack , self._additional , self._command)

    def __setstate__(self , state):
        self._stack , self._additional , self._command = state


