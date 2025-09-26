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
        
#        new_stack = []
#
        def same_el(s1 , s2):
            if s1[1:2] == s2[1:2] == "_":
                if int(s1[2:]) + 1 == int(s2[2:]):
                    return True
                if int(s1[2:]) == int(s2[2:]) + 1:
                    return True
            return False

        new_stack = copy.deepcopy(self._stack)
        if self._command is not None:
            new_stack = list(map(lambda x : '[' + x + ']' if x == self._command else x , new_stack))

        logger.debug(str(new_stack))

        starts = [0]
        for i in range(1 , len(new_stack)):
            if not same_el(new_stack[i] , new_stack[i - 1]):
                starts.append(i)

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
#
#        startend = []
#        start = 0
#        end = 0
#        j = 0
#        for i in range(len(self._stack)):
#            if not same_el(self._stack[i] , self._stack[j]):
#                end = j
#                startend.append((start , end))
#                start = i
#            j = i
#
#        logger.debug(",".join(self._stack))
#        logger.debug(str(startend))

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
            des.append("additional elements : " + str(len(self._additional)))
        if self._command is not None:
            des.append("with command : "  + self._command)

        return "State(" + " , ".join(des) + ")"

    def __getstate__(self):
        return (self._stack , self._additional , self._command)

    def __setstate__(self , state):
        self._stack , self._additional , self._command = state


