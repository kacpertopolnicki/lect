import copy
import logging
import os
import numpy

from log import logger

import draw
from state import State

class Record:
    def __init__(self , configuration , dark_pallete = "default_pallete" , light_pallete = "default_pallete"):

        self._unique = 0

        self._stroke = []

        self._strokes = {"current" : self._stroke}

        self._recordings = dict()

        self._savedstacks = dict()

        self._configuration = copy.deepcopy(configuration)

        self._states = [State([] , None)]
        
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

        self._ar = self._configuration["paper"].getfloat("aspectratio")

        self._every = self._configuration["frames"].getint("every")
        
        self._pause = self._configuration["frames"].getint("pause")

        self._command = ""

        self._set_functions()

        self._samplerate = self._configuration["sound"].getint("sample_rate")

        self._channels = self._configuration["sound"].getint("channels")

        self._framerate = self._configuration["frames"].getint("frame_rate")

        #self._iter = 0

    # PICKLE

    def __getstate__(self):
        return (self._unique ,
                self._strokes , 
                self._recordings ,
                self._savedstacks ,
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
                self._framerate)

    def __setstate__(self , state):
        self._unique , self._strokes , self._recordings , self._savedstacks , self._configuration , self._states , \
        self._dark_paper_color , self._dark_colors , self._light_paper_color , \
        self._light_colors , self._ar , self._every , self._pause , \
        self._samplerate , self._channels , self._framerate = state
        
        self._stroke = []
        self._command = ""
        self._set_functions()

    # modifies _states

    def _append(self , state):
        self._states.append(state)
        logger.debug(str(self))
        top = state.get_top()
        if top is not None and top in self._functions:
            method = self._functions[top]
            new_state = method(self , state)
            self._append(new_state)

    def _make_equalish_time(self , frames , reco):
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
        self._functions = {
                "id" : Record._id ,
                "draw" : Record._draw ,
                "drawshort" : Record._drawshort ,
                "show" : Record._show ,
                "fadein" : Record._fadein ,
                "fadeout" : Record._fadeout ,
                "printout" : Record._printout ,
                "center" : Record._center ,
                "position" : Record._position ,
                "clear" : Record._clear ,
                "savestack" : Record._savestack ,
                "appendstack" : Record._appendstack ,
                "pop" : Record._pop
            }

    def _savestack(self , state):
        stack = state.get_stack()
        stack.pop()
        if len(stack) >= 1:
            name = stack[-1]
            tosave = stack[:-1]
            # todo
            # - this might conflict with _stroke names
            #   make sure new stroke names are unique
            # - same is true for recording names
            if name not in self._savedstacks:
                self._savedstacks[name] = tosave
                return State(tosave , None)
            else:
                return State(stack , None)
        else:
            return State(stack , None)

    def _appendstack(self , state):
        # todo
        # - this can be used to execute functions
        #   use _append to append states
        #   add quote
        stack = state.get_stack()
        stack.pop()
        if len(stack) >= 1:
            name = stack[-1]
            previous = stack[:-1]
            if name in self._savedstacks:
                return State(previous + self._savedstacks[name] , None)
            else:
                return State(stack , None)
        else:
            return State(stack , None)

    def _id(self , state):
        stack = state.get_stack()[:-1]
        additional = copy.deepcopy(state.get_additional())

        return State(stack , additional)

    def _pop(self , state):
        stack = state.get_stack()[:-1]
        additional = None

        if len(stack) > 0:
            stack.pop()

        return State(stack , additional)

    def _clear(self , state):
        return State([] , None)

    def _position(self , state):
        strokes = self.get_current_stack()
        command = strokes.pop()

        if len(strokes) < 1:
            return State(strokes , None)

        xycoord = strokes.pop()

        try:
            xcoord , ycoord = xycoord.split(',')
            xa , xb = xcoord.split('/')
            ya , yb = ycoord.split('/')
            xcoord = (float(xa) / float(xb))
            ycoord = (float(ya) / float(yb)) / self._ar
        except Exception as s:
            return State(strokes , None)

        break_position = -1
        for i in range(len(strokes)):
            s = strokes[i]
            if s == "---":
                break_position = i

        minx , miny , maxx , maxy = None , None , None , None
        for i in range(len(strokes)):
            s = strokes[i]
            if s in self._strokes and i > break_position:
                pts = self._strokes[s]
                for x , y , _ , _ , _ in pts:
                    if minx is None or x < minx:
                        minx = x
                    if miny is None or y < miny:
                        miny = y
                    if maxx is None or x > maxx:
                        maxx = x
                    if maxy is None or y > maxy:
                        maxy = y
       
        if minx is not None and miny is not None and maxx is not None and maxy is not None:

            centerx = 0.5 * (maxx + minx)
            centery = 0.5 * (maxy + miny)

            addx = xcoord - centerx
            addy = ycoord - centery

            logger.debug("centerx centery addx addy : " + str(centerx) + " " + str(centery) + " " + str(addx) + " " + str(addy))

            new_stack = []
            for i in range(len(strokes)):
                s = strokes[i]
                if i > break_position:
                    if s in self._strokes:
                        pts = self._strokes[s]
                        newpts = [
                                    [addx + x , addy + y , p , t , style] 
                                    for x , y , p , t , style in pts]

                        new_stack.append(self.add_full_stroke(newpts))
                    else:
                        new_stack.append(s)
                else:
                    new_stack.append(s)

            return State(new_stack , None)
        else:
            return State(strokes , None)

    def _center(self , state):
        strokes = self.get_current_stack()
        command = strokes.pop()

        break_position = -1
        for i in range(len(strokes)):
            s = strokes[i]
            if s == "---":
                break_position = i

        minx , miny , maxx , maxy = None , None , None , None
        for i in range(len(strokes)):
            s = strokes[i]
            if s in self._strokes and i > break_position:
                pts = self._strokes[s]
                for x , y , _ , _ , _ in pts:
                    if minx is None or x < minx:
                        minx = x
                    if miny is None or y < miny:
                        miny = y
                    if maxx is None or x > maxx:
                        maxx = x
                    if maxy is None or y > maxy:
                        maxy = y
       
        if minx is not None and miny is not None and maxx is not None and maxy is not None:
            addx = (1.0 - (maxx - minx)) / 2.0
            addy = ((1.0 / self._ar) - (maxy - miny)) / 2.0

            new_stack = []
            for i in range(len(strokes)):
                s = strokes[i]
                if i > break_position:
                    if s in self._strokes:
                        pts = self._strokes[s]
                        newpts = [
                                    [addx + (x - minx) , addy + (y - miny) , p , t , style] 
                                    for x , y , p , t , style in pts]

                        new_stack.append(self.add_full_stroke(newpts))
                    else:
                        new_stack.append(s)
                else:
                    new_stack.append(s)

            return State(new_stack , None)
        else:
            return State(strokes , None)

    def _draw(self , state):
        strokes = self.get_current_stack()
        strokes.pop()

        posbreak = 0
        found = False
        for i in reversed(range(len(strokes))):
            posbreak = i
            if strokes[i] == "---":
                found = True
                break

        before = strokes[:posbreak]
        after = strokes[posbreak:]
        if found:
            after = strokes[posbreak + 1:]

        logger.debug(before)
        logger.debug(after)

        frames_before = []
        for i in range(len(before)):
            s = before[i]
            if s in self._strokes:
                pts = self._strokes[s]
                color = int(pts[0][4]) # todo, instead of parameters
                thickness , red , green , blue , opacity = self._dark_colors[color]
                shapes_list = draw.simple_stroke_shapes(pts , 
                                                        parameters = {
                                                               "thickness" : thickness , 
                                                                "color" : (int(red) , int(green) , int(blue)) ,
                                                                "opacity" : int(opacity)
                                                                })
                frames_before += shapes_list

        rec = [self._recordings[s] for s in after if s in self._recordings]
        reco = None
        if len(rec) > 0:
            reco = numpy.concatenate(rec)
            logger.debug(str(reco.shape))

        frames = []
        for istroke in range(len(after)):
            start = []
            for s in after[:istroke]:
                if s in self._strokes:
                    pts = self._strokes[s]
                    color = int(pts[0][4]) # todo, instead of parameters
                    thickness , red , green , blue , opacity = self._dark_colors[color]
                    shapes_list = draw.simple_stroke_shapes(pts , 
                                                            parameters = {
                                                                   "thickness" : thickness , 
                                                                    "color" : (int(red) , int(green) , int(blue)) ,
                                                                    "opacity" : int(opacity)
                                                                    })
                    start += shapes_list

            if after[istroke] in self._strokes:
                pts = self._strokes[after[istroke]]
                color = int(pts[0][4]) # todo, instead of parameters
                thickness , red , green , blue , opacity = self._dark_colors[color]
                for i in list(range(0 , len(pts) , self._every)) + [len(pts)]:
                    pts_part = pts[:i]
                    shapes_list_part = draw.simple_stroke_shapes(pts_part , 
                                                            parameters = {
                                                                   "thickness" : thickness , 
                                                                    "color" : (int(red) , int(green) , int(blue)) ,
                                                                    "opacity" : int(opacity)
                                                                    })
                    frames.append(frames_before + start + shapes_list_part)
            elif after[istroke] == "pause":
                for _ in range(self._pause):
                    frames.append(frames_before + start)        

        frames , reco = self._make_equalish_time(frames , reco)
        return State(strokes , {'frames' : frames , 'recording' : reco})

    def _drawshort(self , state):
        strokes = self.get_current_stack()
        strokes.pop()

        br , bg , bb = self._dark_paper_color
        
        posbreak = 0
        found = False
        for i in reversed(range(len(strokes))):
            posbreak = i
            if strokes[i] == "---":
                found = True
                break

        before = strokes[:posbreak]
        after = strokes[posbreak:]
        if found:
            after = strokes[posbreak + 1:]

        logger.debug("before : " + str(before))
        logger.debug("after : " + str(after))

        frames_before = []
        for i in range(len(before)):
            s = before[i]
            if s in self._strokes:
                pts = self._strokes[s]
                color = int(pts[0][4]) # todo, instead of parameters
                thickness , red , green , blue , opacity = self._dark_colors[color]
                shapes_list = draw.simple_stroke_shapes(pts , 
                                                        parameters = {
                                                               "thickness" : thickness , 
                                                                "color" : (int(red) , int(green) , int(blue)) ,
                                                                "opacity" : int(opacity)
                                                                })
                frames_before += shapes_list

        rec = [self._recordings[s] for s in after if s in self._recordings]
        reco = None
        if len(rec) > 0:
            reco = numpy.concatenate(rec)
            logger.debug(str(reco.shape))
        frames = []
        
        for istroke in range(len(after)):
            start = []
            for s in after[:istroke]:
                if s in self._strokes:
                    pts = self._strokes[s]
                    color = int(pts[0][4]) # todo, instead of parameters
                    thickness , red , green , blue , opacity = self._dark_colors[color]
                    shapes_list = draw.simple_stroke_shapes(pts , 
                                                            parameters = {
                                                                   "thickness" : thickness , 
                                                                    "color" : (int(red) , int(green) , int(blue)) ,
                                                                    "opacity" : int(opacity)
                                                                    })
                    start += shapes_list

            if after[istroke] in self._strokes:
                pts = self._strokes[after[istroke]]
                color = int(pts[0][4]) # todo, instead of parameters
                thickness , red , green , blue , opacity = self._dark_colors[color]
                for i in list(range(0 , len(pts) , self._every)) + [len(pts)]:
                    pts_part = pts[:i]
                    shapes_list_part = draw.simple_stroke_shapes(pts_part , 
                                                            parameters = {
                                                                   "thickness" : thickness , 
                                                                    "color" : (int(red) , int(green) , int(blue)) ,
                                                                    "opacity" : int(opacity)
                                                                    })
                    frames.append(frames_before + start + shapes_list_part)
            elif after[istroke] == "pause":
                for _ in range(self._pause):
                    frames.append(frames_before + start)

        for i in reversed(range(2 * self._pause + 1)):
            t = float(i) / (2 * self._pause)
            f = []
            for istroke in range(len(after)):
                s = after[istroke]
                if s in self._strokes:
                    pts = self._strokes[s]
                    color = int(pts[0][4]) # todo, instead of parameters
                    thickness , red , green , blue , opacity = self._dark_colors[color]
                    shapes_list_part = draw.simple_stroke_shapes(pts , 
                                                            parameters = {
                                                                   "thickness" : thickness , 
                                                                    "color" : (
                                                                        int(t * red + (1.0 - t) * br) , 
                                                                        int(t * green + (1.0 - t) * bg) , 
                                                                        int(t * blue + (1.0 - t) * bb)) ,
                                                                    "opacity" : int(opacity)
                                                                    })
                    f += frames_before + shapes_list_part
            frames.append(f)

            frames , reco = self._make_equalish_time(frames , reco)
            return State(before , {'frames' : frames , 'recording' : reco})

    def _printout(self , state):
        stack = self.get_current_stack()
        stack.pop()

        strokes = []
        
        for s in stack:
            if s in self._strokes:
                strokes.append(s)
        
        frame = []
        for s in strokes:
            pts = self._strokes[s]
            color = int(pts[0][4]) # todo, instead of parameters
            thickness , red , green , blue , opacity = self._light_colors[color]
            shapes_list_part = draw.simple_stroke_shapes(pts , 
                                                    parameters = {
                                                           "thickness" : thickness , 
                                                            "color" : (
                                                                int(red) , 
                                                                int(green) , 
                                                                int(blue)) ,
                                                            "opacity" : int(opacity)
                                                            })
            frame += shapes_list_part

        return State(stack , {"printout" : frame})

    def _show(self , state):
        stack = self.get_current_stack()

        strokes = []

        for s in stack:
            if s in self._strokes:
                strokes.append(s)

        br , bg , bb = self._dark_paper_color

        frames = []

        for i in range(2 * self._pause + 1):
            t = float(i) / (2 * self._pause)
            f = []
            for s in strokes:
                pts = self._strokes[s]
                color = int(pts[0][4]) # todo, instead of parameters
                thickness , red , green , blue , opacity = self._dark_colors[color]
                shapes_list_part = draw.simple_stroke_shapes(pts , 
                                                        parameters = {
                                                               "thickness" : thickness , 
                                                                "color" : (
                                                                    int(t * red + (1.0 - t) * br) , 
                                                                    int(t * green + (1.0 - t) * bg) , 
                                                                    int(t * blue + (1.0 - t) * bb)) ,
                                                                "opacity" : int(opacity)
                                                                })
                f += shapes_list_part
            frames.append(f)
        
        rec = [self._recordings[s] for s in stack if s in self._recordings]
        reco = None
        if len(rec) > 0:
            reco = numpy.concatenate(rec)
            logger.debug(str(reco.shape))

        for i in reversed(range(2 * self._pause + 1)):
            t = float(i) / (2 * self._pause)
            f = []
            for s in strokes:
                pts = self._strokes[s]
                color = int(pts[0][4]) # todo, instead of parameters
                thickness , red , green , blue , opacity = self._dark_colors[color]
                shapes_list_part = draw.simple_stroke_shapes(pts , 
                                                        parameters = {
                                                               "thickness" : thickness , 
                                                                "color" : (
                                                                    int(t * red + (1.0 - t) * br) , 
                                                                    int(t * green + (1.0 - t) * bg) , 
                                                                    int(t * blue + (1.0 - t) * bb)) ,
                                                                "opacity" : int(opacity)
                                                                })
                f += shapes_list_part
            frames.append(f)

        frames , reco = self._make_equalish_time(frames , reco)
        return State([] , {'frames' : frames , 'recording' : reco})
 
    def _fadeout(self , state):
        stack = self.get_current_stack()

        strokes = []

        for s in stack:
            if s in self._strokes:
                strokes.append(s)

        br , bg , bb = self._dark_paper_color

        frames = []

        for i in reversed(range(2 * self._pause + 1)):
            t = float(i) / (2 * self._pause)
            f = []
            for s in strokes:
                pts = self._strokes[s]
                color = int(pts[0][4]) # todo, instead of parameters
                thickness , red , green , blue , opacity = self._dark_colors[color]
                shapes_list_part = draw.simple_stroke_shapes(pts , 
                                                        parameters = {
                                                               "thickness" : thickness , 
                                                                "color" : (
                                                                    int(t * red + (1.0 - t) * br) , 
                                                                    int(t * green + (1.0 - t) * bg) , 
                                                                    int(t * blue + (1.0 - t) * bb)) ,
                                                                "opacity" : int(opacity)
                                                                })
                f += shapes_list_part
            frames.append(f)

        frames , reco = self._make_equalish_time(frames , None)
        return State([] , {'frames' : frames , 'recording' : reco})

    def _fadein(self , state):
        stack = self.get_current_stack()
        stack.pop()

        strokes = []

        for s in stack:
            if s in self._strokes:
                strokes.append(s)

        br , bg , bb = self._dark_paper_color

        frames = []

        for i in range(2 * self._pause + 1):
            t = float(i) / (2 * self._pause)
            f = []
            for s in strokes:
                pts = self._strokes[s]
                color = int(pts[0][4]) # todo, instead of parameters
                thickness , red , green , blue , opacity = self._dark_colors[color]
                shapes_list_part = draw.simple_stroke_shapes(pts , 
                                                        parameters = {
                                                               "thickness" : thickness , 
                                                                "color" : (
                                                                    int(t * red + (1.0 - t) * br) , 
                                                                    int(t * green + (1.0 - t) * bg) , 
                                                                    int(t * blue + (1.0 - t) * bb)) ,
                                                                "opacity" : int(opacity)
                                                                })
                f += shapes_list_part
            frames.append(f)

        frames , reco = self._make_equalish_time(frames , None)
        return State(stack , {'frames' : frames , 'recording' : reco})

    # for interacting

    def add_full_stroke(self , points):

        pts = copy.deepcopy(points)

        name = "s_" + str(self._unique)
        self._unique += 1
       
        logger.debug("Adding full stroke " + name + " with length " + str(len(pts)) + ".")
        
        self._strokes[name] = pts

        return name

    def add_sound(self , sound):

        snd = sound.copy()

        name = "r_" + str(self._unique)
        self._unique += 1
       
        logger.debug("Adding sound " + name + " with length " + str(snd.shape) + ".")
        
        self._recordings[name] = snd
                
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
            self._stroke.append([x , y , p , t , c])
            self._strokes["current"] = self._stroke

    def add_to_command(self , char):
        logger.debug("add_to_command(\"" + char + "\")")
        if char == '\n':
            if len(self._command.strip()) > 0:
                state = self._states[-1]
                new_state = state.add_to_program(self._command.strip())
                self._append(new_state)

                self._command = ""
                state = self._states[-1]
        elif char == chr(8):
            self._command = self._command[:-1]
        else:
            self._command += char

#    def change_command(self , s):
#        self._command = s

    def add_command(self , command):
        logger.debug("add_command(\"" + command + "\")")

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
            logger.debug("Commands after cut : " + str(commands))
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

    def reexecute(self , cursor = None):
        pos = len(self._states) - 1
        if cursor is not None:
            pos = cursor % len(self._states)
        state = self._states.pop()
        self._append(state)

    def get_current_strokes(self , cursor = None):
        stack = None
        if cursor is None:
            stack = self._states[-1].get_stack()
        else:
            stack = self._states[cursor % len(self._states)].get_stack()
      
        return [s for s in stack if s in self._strokes]

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

#    def get_all_frames(self):
#        f = []
#        for s in self._states:
#            additional = s.get_additional()
#            if additional is not None:
#                f += additional['frames']
#        return f

#    def get_printout_frames(self):
#        f = []
#        for s in self._states:
#            additional = s.get_additional()
#            if additional is not None and 'printout' in additional:
#                f.append(additional['printout'])
#        return f

    #

    def __len__(self):
        return len(self._states)

    def __str__(self):
        statelist = "\n , ".join([str(self._states[i]) 
                 for i in range(len(self._states))])
        string = "Record(\n" + statelist + "\n)"
        return string
    
    def nicestr(self , cursor = None , width = 1000 , height = 1000 , additional = []):
        #statelist = ["  " + format(i , '5d') + " : " + self._states[i].nicestr(width = width) 
        #         for i in range(len(self._states))]
        statelist = ["  " + self._states[i].nicestr(width = width - 2) 
                 for i in range(len(self._states))]
        if cursor is not None:
            pos = cursor % len(self._states)
            #statelist[pos] = "| " + format(pos , '5d') + " : " + self._states[pos].nicestr(width = width) 
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
            if end > len(self._states):
                sub = end - len(self._states)
                start -= sub
                end -= sub

        #logger.debug("pos , height , start , end , len(self._states) : " + str(pos) + " " + str(height) + " " + str(start) + " " + str(end) + " " + str(len(self._states)))

        if len(statelist) > height - 3:
            #string = "    ... : ...\n" + "\n".join(statelist[-(height - 3):])
            #string = "    ... : ...\n" + "\n".join(statelist[start : end])
            string = "\n".join(statelist[start : end])
            return string
        else:
            string = "\n".join(statelist)
            return string
