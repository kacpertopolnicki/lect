import copy
import logging
import os

from log import logger
import draw

#RECORD_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

# sauce : https://www.geeksforgeeks.org/python/logging-in-python/ 
#logging.basicConfig(filename = os.path.join(RECORD_DIRECTORY , "log_record") , 
#                    filemode = "w" , 
#                    format='%(message)s   [%(levelname)s|%(filename)s|%(lineno)d]')
#logger = logging.getLogger()
#logger.setLevel(logging.DEBUG)

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
        if self._additional is not None:
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

class Record:
    def __init__(self , configuration , dark_pallete = "default_pallete" , light_pallete = "default_pallete"):

        self._stroke = []

        self._strokes = {"current" : self._stroke}

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

        self._iter = 0

    # PICKLE

    def __getstate__(self):
        return (self._strokes , 
                self._configuration , 
                self._states , 
                self._dark_paper_color ,
                self._dark_colors , 
                self._light_paper_color ,
                self._light_colors , 
                self._ar , 
                self._every , 
                self._pause)

    def __setstate__(self , state):
        self._strokes , self._configuration , self._states , \
        self._dark_paper_color , self._dark_colors , self._light_paper_color , \
        self._light_colors , self._ar , self._every , self._pause = state
        
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

    # _functions

    def _set_functions(self):
        self._functions = {
                "id" : Record._id ,
                "draw" : Record._draw ,
                "drawtemp" : Record._drawtemp ,
                "show" : Record._show ,
                "center" : Record._center ,
                "clear" : Record._clear ,
                "pop" : Record._pop
            }

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

        frames = []
        for istroke in range(len(strokes)):
            start = []
            for s in strokes[:istroke]:
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

            if strokes[istroke] in self._strokes:
                pts = self._strokes[strokes[istroke]]
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
                    frames.append(start + shapes_list_part)
            elif strokes[istroke] == "pause":
                for _ in range(self._pause):
                    frames.append(start)

        return State(strokes , {'frames' : frames , 'printout' : frames[-1]})

    def _drawtemp(self , state):
        strokes = self.get_current_stack()
        strokes.pop()

        posbreak = 0
        for i in reversed(range(len(strokes))):
            posbreak = i
            if strokes[i] == "---":
                break

        before = strokes[:posbreak]
        after = strokes[posbreak + 1:]

        logger.debug("before : " + str(before))
        logger.debug("after : " + str(after))

        frames_before = []
        for i in range(len(before)):
            s = before[i]
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
                thickness , red , green , blue , opacity = self._light_colors[color]
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
                    frames.append(start)

        return State(before , {'frames' : frames , 'printout' : frames[-1]})

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

        printout = frames[-1]

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

        return State([] , {'frames' : frames , 'printout' : printout})
        

    # for interacting

    def add_full_stroke(self , points):

        pts = copy.deepcopy(points)

        name = "s_" + str(len(self._strokes))
       
        logger.debug("Adding full stroke " + name + " with length " + str(len(pts)) + ".")
        
        self._strokes[name] = pts

        return name

    def add_to_stroke(self , x , y , p , t , c):
        if p == 0:
            if len(self._stroke) > 1:
                name = "s_" + str(len(self._strokes))
               
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
            state = self._states[-1]
            new_state = state.add_to_program(self._command)
            self._append(new_state)

            self._command = ""
            state = self._states[-1]
        elif char == chr(8):
            self._command = self._command[:-1]
        else:
            self._command += char

    def change_command(self , s):
        self._command = s

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
            return additional['frames']
        else:
            return None

    def get_all_frames(self):
        f = []
        for s in self._states:
            additional = s.get_additional()
            if additional is not None:
                f += additional['frames']
        return f

    def get_printout_frames(self):
        f = []
        for s in self._states:
            additional = s.get_additional()
            if additional is not None and 'printout' in additional:
                f.append(additional['printout'])
        return f

    # 

    def __str__(self):
        statelist = "\n , ".join([str(self._states[i]) 
                 for i in range(len(self._states))])
        string = "Record(\n" + statelist + "\n)"
        return string
    
    def nicestr(self , cursor = None , width = 1000 , height = 1000):
        statelist = ["  " + format(i , '5d') + " : " + self._states[i].nicestr(width = width) 
                 for i in range(len(self._states))]
        if cursor is not None:
            pos = cursor % len(self._states)
            statelist[pos] = "| " + format(pos , '5d') + " : " + self._states[pos].nicestr(width = width) 

        start = len(statelist) - (height - 3) - 1
        end = len(statelist) - 1

        if cursor is not None:
            before = 2
            pos = cursor % len(self._states)
            after = (height - 4) - before
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

        logger.debug("pos , height , start , end , len(self._states) : " + str(pos) + " " + str(height) + " " + str(start) + " " + str(end) + " " + str(len(self._states)))

        if len(statelist) > height - 3:
            #string = "    ... : ...\n" + "\n".join(statelist[-(height - 3):])
            string = "    ... : ...\n" + "\n".join(statelist[start : end])
            return string
        else:
            string = "\n".join(statelist)
            return string
