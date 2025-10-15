import copy
import logging
import os
import numpy

from log import logger

import draw
from state import State

class Record:
    def __init__(self , configuration , dark_pallete = "default_pallete" , light_pallete = "default_pallete"):

        # unique number for stroke and image names

        self._unique = 0

        # temporary list of stroke daa

        self._stroke = []

        # dictionaries of strokes, recordings and images

        self._strokes = {"current" : self._stroke}

        self._recordings = dict()

        self._images = dict()
        
        # configuration

        self._configuration = copy.deepcopy(configuration)

        # list of states, initialized with a state containing an empty stack

        self._states = [State([] , None)]
        
        # colors

        self._dark_paper_color = list(map(int , self._configuration[dark_pallete]["paper_color"].split(",")))
        
        self._dark_colors =  [
                            list(map(float , self._configuration[dark_pallete][c].split(",")))
                            for c in    ["color_0" , "color_1" , "color_2" , "color_3" , "color_4" ,
                                         "color_5" , "color_6" , "color_7" , "color_8" , "color_9"
                                        ]
                        ]
        
        self._light_paper_color = list(map(int , self._configuration[light_pallete]["paper_color"].split(",")))
        
        self._light_colors =  [
                            list(map(float , self._configuration[light_pallete][c].split(",")))
                            for c in    ["color_0" , "color_1" , "color_2" , "color_3" , "color_4" ,
                                         "color_5" , "color_6" , "color_7" , "color_8" , "color_9"
                                        ]
                            ]

        # aspect ratio

        self._ar = self._configuration["paper"].getfloat("aspectratio")

        # skip self._every frames when drawing text

        self._every = self._configuration["frames"].getint("every")
       
        # length of pause in frames

        self._pause = self._configuration["frames"].getint("pause")

        # temporary string containing the command

        self._command = ""

        # read functions from stackfunctions.py

        self._set_functions()

        # for sound

        self._samplerate = self._configuration["sound"].getint("sample_rate")

        self._channels = self._configuration["sound"].getint("channels")
       
        # todo, is this used? 

        self._fade = self._configuration["sound"].getfloat("fade")

        # frame rate

        self._framerate = self._configuration["frames"].getint("frame_rate")

        # (minimum length of stroke segment)**2

        self._min = 1.0 / (self._configuration["frames"].getint("width")**2)
        
        # for hashing

        self._hash_hits = 0
        self._hash_misses = 0

        self._hashed_function_values = dict()

    # for hashing

    def _record_hash(self , f):
        def g(r , stack , memory):
            #h = hash((tuple(stack) , f.__name__))
            # todo can this be improved
            stackstr = ",".join(stack)
            memorystr = [str(k) + " : " + str(memory[k]) for k in memory]
            memorystr.sort() # this might be important for hashing dictionaries
            memorystr = ",".join(memorystr)
            h = "stack " + stackstr + " memory " + memorystr + " functionname " + f.__name__
            if h in self._hashed_function_values:
                self._hash_hits += 1
                logger.debug("In hashed functions, hits misses : " + str(self._hash_hits) + " " + str(self._hash_misses))
                return self._hashed_function_values[h]
            else:
                val = f(r , stack , memory)
                self._hashed_function_values[h] = val
                self._hash_misses += 1
                logger.debug("In hashed functions, hits misses : " + str(self._hash_hits) + " " + str(self._hash_misses))
                return val
        return g

    # PICKLE

    def __getstate__(self):
        return (self._unique ,
                self._strokes , 
                self._recordings ,
                self._images ,
                self._configuration , 
                self._states , 
                self._dark_paper_color ,
                self._dark_colors , 
                self._light_paper_color ,
                self._light_colors , 
                self._ar , 
                self._every , 
                self._pause ,
                self._samplerate , 
                self._channels ,
                self._fade ,
                self._framerate ,
                self._min ,
                self._hashed_function_values)

    def __setstate__(self , state):
        self._unique , self._strokes , self._recordings , self._images , \
        self._configuration , self._states , \
        self._dark_paper_color , self._dark_colors , self._light_paper_color , \
        self._light_colors , self._ar , self._every , self._pause , \
        self._samplerate , self._channels , self._fade , self._framerate , \
        self._min , self._hashed_function_values = state
       
        self._hash_hits = 0
        self._hash_misses = 0

        self._stroke = []
        self._command = ""
        self._set_functions()

    # modifies _states

    def _append(self , state):
        to_append = state
        if len(self._states) > 0:
            to_append = state.join_memories(self._states[-1])
        self._states.append(to_append)
        top = to_append.get_top()
        if top is not None and top in self._functions:
            method = self._functions[top]
            new_state = method(self , to_append.get_stack() , to_append.get_memory())
            self._append(new_state)

    def _make_equalish_time(self , frames , reco):
        # todo, call this in _append instead of individual functions
        if reco is not None:
            animation_time = len(frames) / self._framerate
            recording_time = reco.shape[0] / self._samplerate
            if recording_time > animation_time:
                last_frame = frames[-1]
                to_append = int((recording_time - animation_time) * self._framerate)
                for _ in range(to_append):
                    frames.append(last_frame)
                new_recording_length = int((len(frames) / self._framerate) * self._samplerate)
                reco = reco[:new_recording_length]
            else:
                new_recording_length = (len(frames) / self._framerate) * self._samplerate
                old_recording_length = reco.shape[0]

                additional_shape = list(reco.shape)
                additional_shape[0] = int(new_recording_length - old_recording_length)
                additional_shape = tuple(additional_shape)

                zeros = numpy.zeros(shape = additional_shape , dtype = reco.dtype)

                reco = numpy.concatenate([reco , zeros])
            return frames , reco
        else:
            animation_time = len(frames) / self._framerate
            recording_length = int(animation_time * self._samplerate)

            reco = numpy.zeros(shape = (recording_length , self._channels) , dtype = 'int16')
            return frames , reco

    # _functions

    def _set_functions(self):
        import stackfunctions
        self._functions = dict()
        for x in stackfunctions.__dict__:
            if "stack_function" in x:
                fun = stackfunctions.__dict__[x]
                self._functions[x[15:]] = self._record_hash(fun) 
    #

    def _add_full_stroke(self , points):

        pts = copy.deepcopy(points)

        name = "s_" + str(self._unique)
        self._unique += 1
       
        logger.debug("Adding full stroke " + name + " with length " + str(len(pts)) + ".")
        
        self._strokes[name] = pts

        return name

    def _add_full_image(self , image):

        name = "i_" + str(self._unique)
        self._unique += 1
       
        logger.debug("Adding full image " + name + ".")
        
        self._images[name] = image

        return name

    # for interacting

    def add_sound(self , sound):

        snd = sound.copy()

        name = "r_" + str(self._unique)
        self._unique += 1
       
        logger.debug("Adding sound " + name + " with length " + str(snd.shape) + ".")
      
        fadenum = int(self._fade * self._samplerate)

        if snd.shape[0] > 2 * fadenum:
            snd = snd[fadenum : -fadenum]
            if snd.shape[0] > fadenum:
                # todo, mask to __init__
                mask = numpy.linspace(0.0 , 1.0 , fadenum)
                shpe = list(snd.shape)
                shpe[0] = fadenum
                shpe = tuple(shpe)
                mask = mask.reshape(shpe)

                snd[:fadenum] = (snd[:fadenum] * mask).astype(snd.dtype)

                snd[-fadenum:] = (snd[-fadenum:] * mask).astype(snd.dtype)

        self._recordings[name] = snd
                
        state = self._states[-1]
        new_state = state.add_to_program(name)
        self._append(new_state)

    def add_image(self , image):
 
        if image.shape[2] == 3:

            img = image.copy()

            name = "i_" + str(self._unique)
            self._unique += 1

            logger.debug("Adding image " + name + " with shape " + str(img.shape) + ".")

            ar = image.shape[1] / image.shape[0]

            if ar <= self._ar:
                # fit height
                w = ar / self._ar
                h = 1.0 / self._ar
                x0 = 0.5 - 0.5 * w
                y0 = 0.0
                self._images[name] = {"type" : "image" , 
                                      "data" : img , 
                                      "ar" : ar , 
                                      'x0' : x0 , 'y0' : y0 , 
                                      'w' : w , 'h' : h ,
                                      "opacity" : 1.0}
            else:
                # fit width
                w = 1.0
                h = 1.0 / ar
                x0 = 0.0
                y0 = 0.5 - 0.5 * h
                self._images[name] = {"type" : "image" , 
                                      "data" : img , 
                                      "ar" : ar , 
                                      'x0' : x0 , 'y0' : y0 , 
                                      'w' : w , 'h' : h ,
                                      "opacity" : 1.0}
                    
            state = self._states[-1]
            new_state = state.add_to_program(name)
            self._append(new_state)


    def add_to_stroke(self , x , y , p , t , c):
        if p == 0:
            if len(self._stroke) > 1:
                name = "s_" + str(self._unique)
                self._unique += 1
               
                logger.debug("Adding stroke " + name + " with length " + str(len(self._stroke)) + ".")
                
                self._strokes[name] = self._stroke
                self._stroke = []
                self._strokes["current"] = self._stroke

                state = self._states[-1]
                new_state = state.add_to_program(name)
                self._append(new_state)
        else:
            ok = True
            if len(self._stroke) > 0:
                xp , yp , _ , _ , _ = self._stroke[-1]
                ok = ok and (xp - x)**2 + (yp  - y)**2 > self._min
            if ok:                
                self._stroke.append([x , y , p , t , c])
                self._strokes["current"] = self._stroke

    def add_to_command(self , char):
        if char == '\n':
            # commands with _ are reserved
            if len(self._command.strip()) > 0 and '_' not in self._command.strip():
                state = self._states[-1]
                new_state = state.add_to_program(self._command.strip())
                self._append(new_state)

                self._command = ""
                state = self._states[-1]
        elif char == chr(8):
            self._command = self._command[:-1]
        else:
            self._command += char

    def add_command(self , command):
        state = self._states[-1]
        new_state = state.add_to_program(command)
        self._append(new_state)

    def get_current_command(self):
        return copy.deepcopy(self._command)

    def modify_after_cursor(self , cursor , save_commands = True):
        pos = cursor % len(self._states)

        if pos != 0:

            bef = self._states[:pos]
            aft = self._states[pos:]

            self._states = bef

            commands = []
            for s in aft:
                c = s.get_command()
                if c is not None:
                    commands.append(c)
            if save_commands:
                return commands
            else:
                return None
        else:
            return None

    def get_configuration(self):
        return copy.deepcopy(self._configuration)

    def get_stroke(self , name):
        if name in self._strokes:
            return copy.deepcopy(self._strokes[name])
        else:
            return None
    
    def get_image(self , name):
        if name in self._images:
            #todo return copy.deepcopy(self._images[name])
            return self._images[name]
        else:
            return None

    def reexecute(self , cursor = None):
        pos = len(self._states) - 1
        if cursor is not None:
            pos = cursor % len(self._states)
        state = self._states.pop()
        self._append(state)

    def get_type(self , s):
        if s in self._strokes:
            return "stroke"
        if s in self._images:
            return "image"
        return None

    def get_current_strokes_images(self , cursor = None):
        stack = None
        if cursor is None:
            stack = self._states[-1].get_stack()
        else:
            stack = self._states[cursor % len(self._states)].get_stack()
      
        return [s for s in stack if (s in self._strokes) or (s in self._images)]

    def get_current_stack(self , cursor = None):
        stack = None
        if cursor is None:
            stack = self._states[-1].get_stack()
        else:
            stack = self._states[cursor % len(self._states)].get_stack()
      
        return stack

    def get_frames(self , cursor = None):
        state = None
        if cursor is None:
            state = self._states[-1]
        else:
            state = self._states[cursor % len(self._states)]

        additional = state.get_additional()
        if additional is not None:
            return additional
        else:
            return None

    def get_all_additional(self):
        f = []
        for s in self._states:
            additional = s.get_additional()
            if additional is not None:
                f.append(additional)
        return f

    def __len__(self):
        return len(self._states)

    def __str__(self):
        statelist = "\n , ".join([str(self._states[i]) 
                 for i in range(len(self._states))])
        string = "Record(\n" + statelist + "\n)"
        return string
    
    def nicestr(self , cursor = None , width = 1000 , height = 1000 , additional = []):
        if len(self._states) == 0:
            return ""

        statelist = ["  " + self._states[i].nicestr(width = width - 2) 
                 for i in range(len(self._states))]
        statelist[0] = "0 " + self._states[0].nicestr(width = width - 2)
        if cursor is not None:
            pos = cursor % len(self._states)
            statelist[pos] = "| " + self._states[pos].nicestr(width = width - 2) 

        statelist += additional

        start = len(statelist) - (height - 2) - 1
        end = len(statelist) - 1

        if cursor is not None:
            before = 2
            pos = cursor % len(self._states)
            after = (height - 3) - before
            start = pos - before
            end = pos + after
            if start < 0:
                add = -start
                start += add
                end += add
            if end > len(statelist):
                sub = end - len(statelist)
                start -= sub
                end -= sub

        if len(statelist) > height - 3:
            string = "\n".join(statelist[start : end])
            return string
        else:
            string = "\n".join(statelist)
            return string
