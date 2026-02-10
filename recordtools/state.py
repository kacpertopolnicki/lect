"""
This module implements the class State whose objects
contain information about the current state the application.

As the execution of the program progresses, discrete states
are appended to a list of states and each consecutive state
may be calculated from the preceeding state. This allows 
reverting back to any given point in the programms history.

Used by:
    * stackfunctions.py (majority of cases)
    * record.py
"""

import copy
import pickle
import zlib

from .log import logger

class State:
    def __init__(self , stack , additional = None , command = None , memory = None):
        """
        Create and initialize a State object. It is intended to be immutable
        and holds information supplied in the arguments.
       
        Todo / note:
            * The `command` argument is used only in State. This may be removed
              from the argument list.

            * Add type hints.

        Args:
            stack (list) : List of strokes name, recording names and other commands / arguments.
            additional (dict) : Additional data that was calculated from the strokes
                in a previous state. The dictionary may contain two keys. The `frames`
                element contains a list of frames. The `recording` element contains an audio
                recording in the form of a numpy array. Note that the additoinal information
                is stored in compressed form using a combination of zlib and pickle.
            memory (dict) : Dictionary in the form {<some name> : <some list of stroke names>, ...}
            command : DO NOT USE, to be removed.
        """
        self._stack = copy.deepcopy(stack)
        if additional is not None:
            # sauce : https://stackoverflow.com/questions/19500530/compress-python-object-in-memory
            self._additional = zlib.compress(pickle.dumps(additional))
        else:
            self._additional = None
        self._command = command
        self._memory = dict()
        if memory is not None:
            self._memory.update(memory)

    def join_memories(self , other):
        """
        Join the saved memories of two states and return a new state. 

        Todo / note:
            * Used only in record.py in function _apend. Can this method be elimiminated?

        Arguments:
            other (State) : Other state with memories to be joined with the 
                memories of `self`.

        Returns:
            State : State with joined memories from self and other.
        """
        new_memory = dict()
        new_memory.update(self._memory)
        new_memory.update(other._memory)
       
        new_stack = copy.deepcopy(self._stack)
        #new_additional = copy.deepcopy(self.get_additional())
        new_additional = self.get_additional()
        new_command = copy.deepcopy(self._command)

        new_state = State(new_stack , 
                          new_additional ,
                          command = new_command ,
                          memory = new_memory)

        return new_state

    def get_memory(self):
        """
        Retun a copy of memories.

        Todo / note:
            * Used only in record.py in function _append. Can this method be elimiminated? 
            * Using deepcopy might be a bit much?

        Returns:
            dict : Dictionary in the form {<some name> : <some list of stroke names>, ...}
        """
        return copy.deepcopy(self._memory)

    def get_stack(self):
        """
        Retun a copy of the stack.

        Todo / note:
            * Used only in record.py in function _append and _get_current_strokes_images. 
            * Using deepcopy might be a bit much?

        Returns:
            list : List of element names in stack.
        """
        return copy.deepcopy(self._stack)

    def get_additional(self):
        """
        Uncompress and return additional data.

        Returns:
            dict: The dictionary may contain two keys. The `frames`
                element contains a list of frames. The `recording` element contains an audio
                recording in the form of a numpy array. 
        """
        if self._additional is not None:
            return pickle.loads(zlib.decompress(self._additional))
        else:
            return None
    
    def get_top(self):
        """
        Retun the top element of the stack.

        Todo / note:
            * Used only in record.py in function _append. Can this method be eliminated? 
            * Using deepcopy might be a bit much?

        Returns:
            str | None : Top element of stack of None if stack contains no elements.
        """
        if len(self._stack) > 0:
            return copy.deepcopy(self._stack[-1])
        else:
            return None

    def get_command(self):
        """
        Returns a command attached to a state.

        Todo / note:
            * Used only in record.py in function modify_after_cursor.

        Returns:
            str | None : Command name or None if there is no command attached to the state.
        """
        return copy.deepcopy(self._command)

    def add_to_program(self , element): # state -> state
        """
        Append a name onto the stack. 

        Todo / note:
            * Can this be used to replace the command argument in __init__?

        Returns:
            State : State with an appended element.
        """
        stack = self.get_stack()
        stack.append(element)
        additional = None

        return State(stack , additional , command = copy.deepcopy(element))

    def nicestr(self , width = 1000):
        """
        Returns a nice representation of the state.

        Arguments:
            width (int) : The width of the text.

        Returns:
            str : The prepresentation of the state.
        """
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
        """
        Returns a basic representation of the state.

        Returns:
            str : The prepresentation of the state.
        """
        des = []
        des.append("stack : " + " ".join(self._stack))
        if self._additional is not None:
            des.append("contains additional elements")
        if self._command is not None:
            des.append("with command : "  + self._command)

        return "State(" + " , ".join(des) + ")"

    def __getstate__(self):
        """
        For the pickle module. Returns a tuple that can be used to reconstruct the state.
        """
        return (self._stack , self._additional , self._command , self._memory)

    def __setstate__(self , state):
        """
        For the pickle module. Reconstructs the state using a tuple of values.
        """
        self._stack , self._additional , self._command , self._memory = state


