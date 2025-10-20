import numpy
import copy
import scipy

from .state import State
from . import draw
from .log import logger

# In principle a subclass of Record could contain
# the following functions as methods. This would
# allow clustering different types of methods
# in different classes.

def stack_function_savestack(self , stack , memory):
    stack.pop()

    posbreak = 0
    found = False
    for i in reversed(range(len(stack))):
        posbreak = i
        if stack[i] == "---":
            found = True
            break

    before = stack[:posbreak]
    after = stack[posbreak:]
    if found:
        after = stack[posbreak + 1:]

    if len(after) >= 1:
        name = after[-1]
        tosave = after[:-1]
        # todo
        # - this might conflict with _stroke names
        #   make sure new stroke names are unique
        # - same is true for recording names
        #if name not in self._savedstacks:
        #    self._savedstacks[name] = tosave
        #    return State(stack , None)
        if name not in memory:
            mem = {name : tosave}
            return State(stack , None , memory = mem)
        else:
            return State(stack , None)
    else:
        return State(stack , None)

def stack_function_appendstack(self , stack , memory):
    # todo
    # - this can be used to execute functions
    #   use _append to append states
    #   add quote
    stack.pop()
    if len(stack) >= 1:
        name = stack[-1]
        previous = stack[:-1]
        #if name in self._savedstacks:
        #    return State(previous + self._savedstacks[name] , None)
        if name in memory:
            return State(previous + memory[name] , None)
        else:
            return State(stack , None)
    else:
        return State(stack , None)

def stack_function_id(self , stack , memory):
    stack.pop()

    return State(stack , [])

def stack_function_pop(self , stack , memory):
    stack.pop()
    additional = None

    if len(stack) > 0:
        stack.pop()

    return State(stack , additional)

def stack_function_clear(self , stack , memory):
    return State([] , None)

def stack_function_move(self , strokes , memory):
    command = strokes.pop()

    if len(strokes) < 1:
        return State(strokes , None)

    xycoord = strokes.pop()

    xcoord , ycoord = None , None

    try:
        xcoord , ycoord = xycoord.split(',')
        xcoord = float(xcoord)
        ycoord = float(ycoord)
    except Exception as s:
        return State(strokes , None)

    break_position = -1
    for i in range(len(strokes)):
        s = strokes[i]
        if s == "---":
            break_position = i

    new_stack = []
    for i in range(len(strokes)):
        s = strokes[i]
        if i > break_position:
            if s in self._strokes:
                pts = self._strokes[s]
                newpts = [
                            [xcoord + x , ycoord + y , p , t , style] 
                            for x , y , p , t , style in pts]

                new_stack.append(self._add_full_stroke(newpts))
            else:
                new_stack.append(s)
        else:
            new_stack.append(s)

    return State(new_stack , None)

def stack_function_position(self , strokes , memory):
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

        new_stack = []
        for i in range(len(strokes)):
            s = strokes[i]
            if i > break_position:
                if s in self._strokes:
                    pts = self._strokes[s]
                    newpts = [
                                [addx + x , addy + y , p , t , style] 
                                for x , y , p , t , style in pts]

                    new_stack.append(self._add_full_stroke(newpts))
                else:
                    new_stack.append(s)
            else:
                new_stack.append(s)

        return State(new_stack , None)
    else:
        return State(strokes , None)

def stack_function_center(self , strokes , memory):
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

                    new_stack.append(self._add_full_stroke(newpts))
                else:
                    new_stack.append(s)
            else:
                new_stack.append(s)

        return State(new_stack , None)
    else:
        return State(strokes , None)

def stack_function_draw(self , strokes , memory):
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
        elif s in self._images:
            img = self._images[s]
            shapes_list = [img]
            frames_before += shapes_list

    rec = [self._recordings[s] for s in after if s in self._recordings]
    reco = None
    if len(rec) > 0:
        reco = numpy.concatenate(rec)

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
            elif s in self._images:
                img = self._images[s]
                shapes_list = [img]
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
        elif after[istroke] in self._images:
            im = self._images[after[istroke]]
            for i in range(2 * self._pause + 1):
                t = float(i) / (2 * self._pause)
                newim = {"type" : "image" ,
                         "data" : im["data"] , 
                         "ar" : im["ar"] , 
                         "x0" : im["x0"] ,
                         "y0" : im["y0"] ,
                         "w" : im["w"] ,
                         "h" : im["h"] ,
                         "opacity" : t}
                frames.append(frames_before + start + [newim])
        elif after[istroke] == "pause":
            for _ in range(self._pause):
                frames.append(frames_before + start)        

    frames , reco = self._make_equalish_time(frames , reco)
    return State(strokes , {'frames' : frames , 'recording' : reco})

def stack_function_drawshort(self , strokes , memory):
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
        elif s in self._images:
            img = self._images[s]
            shapes_list = [img]
            frames_before += shapes_list

    rec = [self._recordings[s] for s in after if s in self._recordings]
    reco = None
    if len(rec) > 0:
        reco = numpy.concatenate(rec)

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
            elif s in self._images:
                img = self._images[s]
                shapes_list = [img]
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
        elif after[istroke] in self._images:
            im = self._images[after[istroke]]
            for i in range(2 * self._pause + 1):
                t = float(i) / (2 * self._pause)
                newim = {"type" : "image" ,
                         "data" : im["data"] , 
                         "ar" : im["ar"] , 
                         "x0" : im["x0"] ,
                         "y0" : im["y0"] ,
                         "w" : im["w"] ,
                         "h" : im["h"] ,
                         "opacity" : t}
                frames.append(frames_before + start + [newim])
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
            elif s in self._images:
                im = self._images[s]
                newim = {"type" : "image" ,
                         "data" : im["data"] , 
                         "ar" : im["ar"] , 
                         "x0" : im["x0"] ,
                         "y0" : im["y0"] ,
                         "w" : im["w"] ,
                         "h" : im["h"] ,
                         "opacity" : t}
                f += frames_before + [newim]
        frames.append(f)

    frames , reco = self._make_equalish_time(frames , reco)
    return State(before , {'frames' : frames , 'recording' : reco})

def stack_function_printout(self , stack , memory):
    stack.pop()

    frame = []
    for s in stack:
        if s in self._strokes:
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
        elif s in self._images:
            img = self._images[s]
            shapes_list = [img]
            frame += shapes_list

    return State(stack , {"printout" : frame})

def stack_function_show(self , strokes , memory):
    br , bg , bb = self._dark_paper_color

    frames = []

    for i in range(2 * self._pause + 1):
        t = float(i) / (2 * self._pause)
        f = []
        for s in strokes:
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
                f += shapes_list_part
            elif s in self._images:
                im = self._images[s]
                newim = {"type" : "image" ,
                         "data" : im["data"] , 
                         "ar" : im["ar"] , 
                         "x0" : im["x0"] ,
                         "y0" : im["y0"] ,
                         "w" : im["w"] ,
                         "h" : im["h"] ,
                         "opacity" : t}
                f += [newim]
        frames.append(f)
    
    rec = [self._recordings[s] for s in strokes if s in self._recordings]
    reco = None
    if len(rec) > 0:
        reco = numpy.concatenate(rec)

    for i in reversed(range(2 * self._pause + 1)):
        t = float(i) / (2 * self._pause)
        f = []
        for s in strokes:
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
                f += shapes_list_part
            elif s in self._images:
                im = self._images[s]
                newim = {"type" : "image" ,
                         "data" : im["data"] , 
                         "ar" : im["ar"] , 
                         "x0" : im["x0"] ,
                         "y0" : im["y0"] ,
                         "w" : im["w"] ,
                         "h" : im["h"] ,
                         "opacity" : t}
                f += [newim]
        frames.append(f)

    frames , reco = self._make_equalish_time(frames , reco)
    return State([] , {'frames' : frames , 'recording' : reco})

def stack_function_fadeout(self , strokes , memory):
    br , bg , bb = self._dark_paper_color

    frames = []

    for i in reversed(range(2 * self._pause + 1)):
        t = float(i) / (2 * self._pause)
        f = []
        for s in strokes:
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
                f += shapes_list_part
            elif s in self._images:
                im = self._images[s]
                newim = {"type" : "image" ,
                         "data" : im["data"] , 
                         "ar" : im["ar"] , 
                         "x0" : im["x0"] ,
                         "y0" : im["y0"] ,
                         "w" : im["w"] ,
                         "h" : im["h"] ,
                         "opacity" : t}
                f += [newim]
        frames.append(f)

    frames , reco = self._make_equalish_time(frames , None)
    return State([] , {'frames' : frames , 'recording' : reco})

def stack_function_disappear(self , strokes , memory):
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
        elif s in self._images:
            img = self._images[s]
            shapes_list = [img]
            frames_before += shapes_list

    rec = [self._recordings[s] for s in after if s in self._recordings]
    reco = None
    if len(rec) > 0:
        reco = numpy.concatenate(rec)

    frames = []

    for i in reversed(range(2 * self._pause + 1)):
        t = float(i) / (2 * self._pause)
        f = []
        for s in after:
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
                f += shapes_list_part
            elif s in self._images:
                im = self._images[s]
                newim = {"type" : "image" ,
                         "data" : im["data"] , 
                         "ar" : im["ar"] , 
                         "x0" : im["x0"] ,
                         "y0" : im["y0"] ,
                         "w" : im["w"] ,
                         "h" : im["h"] ,
                         "opacity" : t}
                f += [newim]
        frames.append(frames_before + f)

    frames , reco = self._make_equalish_time(frames , reco)
    return State(before , {'frames' : frames , 'recording' : reco})

def stack_function_cleanup(self , strokes , memory):
    strokes.pop()
    new_stack = [s for s in strokes if s != '---']
    return State(new_stack)

def stack_function_fadein(self , strokes , memory):
    strokes.pop()

    br , bg , bb = self._dark_paper_color

    frames = []

    for i in range(2 * self._pause + 1):
        t = float(i) / (2 * self._pause)
        f = []
        for s in strokes:
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
                f += shapes_list_part
            elif s in self._images:
                im = self._images[s]
                newim = {"type" : "image" ,
                         "data" : im["data"] , 
                         "ar" : im["ar"] , 
                         "x0" : im["x0"] ,
                         "y0" : im["y0"] ,
                         "w" : im["w"] ,
                         "h" : im["h"] ,
                         "opacity" : t}
                f += [newim]
        frames.append(f)

    frames , reco = self._make_equalish_time(frames , None)
    return State(strokes , {'frames' : frames , 'recording' : reco})

def stack_function_appear(self , strokes , memory):
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
        elif s in self._images:
            img = self._images[s]
            shapes_list = [img]
            frames_before += shapes_list

    rec = [self._recordings[s] for s in after if s in self._recordings]
    reco = None
    if len(rec) > 0:
        reco = numpy.concatenate(rec)

    frames = []

    for i in range(2 * self._pause + 1):
        t = float(i) / (2 * self._pause)
        f = []
        for s in after:
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
                f += shapes_list_part
            elif s in self._images:
                im = self._images[s]
                newim = {"type" : "image" ,
                         "data" : im["data"] , 
                         "ar" : im["ar"] , 
                         "x0" : im["x0"] ,
                         "y0" : im["y0"] ,
                         "w" : im["w"] ,
                         "h" : im["h"] ,
                         "opacity" : t}
                f += [newim]
        frames.append(frames_before + f)

    frames , reco = self._make_equalish_time(frames , reco)
    return State(strokes , {'frames' : frames , 'recording' : reco})

def stack_function_place(self , strokes , memory):
    strokes.pop()

    br , bg , bb = self._dark_paper_color

    frames = []

    for _ in range(2 * self._pause + 1):
        f = []
        for s in strokes:
            if s in self._strokes:
                pts = self._strokes[s]
                color = int(pts[0][4]) # todo, instead of parameters
                thickness , red , green , blue , opacity = self._dark_colors[color]
                shapes_list_part = draw.simple_stroke_shapes(pts , 
                                                        parameters = {
                                                               "thickness" : thickness , 
                                                                "color" : (
                                                                    int(red) , 
                                                                    int(green) , 
                                                                    int(blue)) ,
                                                                "opacity" : int(opacity)
                                                                })
                f += shapes_list_part
            elif s in self._images:
                im = self._images[s]
                newim = {"type" : "image" ,
                         "data" : im["data"] , 
                         "ar" : im["ar"] , 
                         "x0" : im["x0"] ,
                         "y0" : im["y0"] ,
                         "w" : im["w"] ,
                         "h" : im["h"] ,
                         "opacity" : t}
                f += [newim]
        frames.append(f)

    frames , reco = self._make_equalish_time(frames , None)
    return State(strokes , {'frames' : frames , 'recording' : reco})

def stack_function_iposition(self , strokes , memory):
    command = strokes.pop()

    if len(strokes) < 1:
        return State(strokes , None)

    xycoord = strokes.pop()

    xcoord , ycoord , scale = None , None , None
    try:
        xcoord , ycoord , scale = xycoord.split(',')
        xa , xb = xcoord.split('/')
        ya , yb = ycoord.split('/')
        scalea , scaleb = scale.split('/')
        xcoord = (float(xa) / float(xb))
        ycoord = (float(ya) / float(yb)) / self._ar
        scale = (float(scalea) / float(scaleb))
    except Exception as s:
        return State(strokes , None)

    break_position = -1
    for i in range(len(strokes)):
        s = strokes[i]
        if s == "---":
            break_position = i

    new_stack = []
    for i in range(len(strokes)):
        s = strokes[i]
        if i > break_position:
            if s in self._images:
                im = self._images[s]

                newim = {"type" : "image" ,
                         "data" : im["data"] , 
                         "ar" : im["ar"] , 
                         "x0" : xcoord - 0.5 * im["w"] * scale ,
                         "y0" : ycoord - 0.5 * im["h"] * scale ,
                         "w" : im["w"] * scale ,
                         "h" : im["h"] * scale ,
                         "opacity" : im["opacity"]}

                new_stack.append(self._add_full_image(newim))
            else:
                new_stack.append(s)
        else:
            new_stack.append(s)

    return State(new_stack , None)

def stack_function_interpolate(self , strokes , memory):
    strokes.pop()

    strokes_old = copy.deepcopy(strokes)

    numframes = None
    try:
        nf = strokes.pop()
        numframes = int(nf)
    except:
        return State(strokes_old , None)

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
        elif s in self._images:
            img = self._images[s]
            shapes_list = [img]
            frames_before += shapes_list

    rec = [self._recordings[s] for s in after if s in self._recordings]
    reco = None
    if len(rec) > 0:
        reco = numpy.concatenate(rec)

    finalstrokes = []

    frames = []
    ab = [None , None]
    abi = 0
    for s in after:
        #if s in self._savedstacks:
        if s in memory:
            ab[abi] = s
            abi += 1
            abi = abi % 2

        if ab[0] is not None and ab[1] is not None:
            #strokesa = [s for s in self._savedstacks[ab[0]] if s in self._strokes]
            #strokesb = [s for s in self._savedstacks[ab[1]] if s in self._strokes]
            strokesa = [s for s in memory[ab[0]] if s in self._strokes]
            strokesb = [s for s in memory[ab[1]] if s in self._strokes]
            finalstrokes = strokesb
            
            if len(strokesa) == len(strokesb):
                for t1 in numpy.linspace(0.0 , 1.0 , numframes):
                    shapes_list_part = []
                    for i in range(len(strokesa)):
                        sa = strokesa[i]
                        sb = strokesb[i]
                        ptsa = self._strokes[sa]
                        ptsb = self._strokes[sb]

                        if len(ptsa) > 2 and len(ptsb) > 2:
                            npa = numpy.array(ptsa)
                            npb = numpy.array(ptsb)
                            ta = (npa[: , 3] - npa[0 , 3]) / (npa[-1 , 3] - npa[0 , 3])
                            tb = (npb[: , 3] - npb[0 , 3]) / (npb[-1 , 3] - npb[0 , 3])

                            interpolator = scipy.interpolate.make_interp_spline(ta , npa[: , [0 , 1 , 2]] , k = 1)

                            newa = interpolator(tb)

                            newpts = []
                            for i in range(newa.shape[0]):
                                newx = newa[i , 0] * (1.0 - t1) + npb[i , 0] * t1
                                newy = newa[i , 1] * (1.0 - t1) + npb[i , 1] * t1
                                newp = newa[i , 2] * (1.0 - t1) + npb[i , 2] * t1
                                if newx < 0:
                                    newx = 0.0
                                elif newx > 1:
                                    newx = 1.0
                                if newy < 0:
                                    newy = 0.0
                                elif newy > 1.0 / self._ar:
                                    newy = 1.0 / self._ar
                                if newp < 0:
                                    newp = 0.0
                                elif newp > 1:
                                    newp = 1.0
                                newpts.append(
                                        [newx,
                                         newy,
                                         newp,
                                         ptsb[i][3] , ptsb[i][4]]
                                        )
                            color = int(ptsb[0][4]) # todo, instead of parameters
                            color = int(ptsb[0][4]) # todo, instead of parameters
                            thickness , red , green , blue , opacity = self._dark_colors[color]
                            shapes_list_part += draw.simple_stroke_shapes(newpts , 
                                                                    parameters = {
                                                                           "thickness" : thickness , 
                                                                            "color" : (int(red) , int(green) , int(blue)) ,
                                                                            "opacity" : int(opacity)
                                                                            })
                    frames.append(frames_before + shapes_list_part)

                ab = [None , None]

    frames , reco = self._make_equalish_time(frames , reco)
    return State(before + finalstrokes , {'frames' : frames , 'recording' : reco})

def stack_function_animate(self , strokes , memory):
    strokes.pop()

    strokes_old = copy.deepcopy(strokes)

    numframes = None
    try:
        nf = strokes.pop()
        numframes = int(nf)
    except:
        return State(strokes_old , None)

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
        elif s in self._images:
            img = self._images[s]
            shapes_list = [img]
            frames_before += shapes_list

    rec = [self._recordings[s] for s in after if s in self._recordings]
    reco = None
    if len(rec) > 0:
        reco = numpy.concatenate(rec)

    finalstrokes = []

    frames = []
    for t1 in numpy.linspace(0.0 , 1.0 , numframes):
        shapes_list_part = []
        ab = [None , None]
        abi = 0
        for s in after:
            #if s in self._savedstacks:
            if s in memory:
                ab[abi] = s
                abi += 1
                abi = abi % 2

            if ab[0] is not None and ab[1] is not None:
                #strokesa = [s for s in self._savedstacks[ab[0]] if s in self._strokes]
                #strokesb = [s for s in self._savedstacks[ab[1]] if s in self._strokes]
                strokesa = [s for s in memory[ab[0]] if s in self._strokes]
                strokesb = [s for s in memory[ab[1]] if s in self._strokes]
                
                if len(strokesa) == len(strokesb):
                    for i in range(len(strokesa)):
                        sa = strokesa[i]
                        sb = strokesb[i]
                        ptsa = self._strokes[sa]
                        ptsb = self._strokes[sb]

                        if len(ptsa) > 2 and len(ptsb) > 2:
                            if t1 == 0.0:
                                finalstrokes += strokesb
                            npa = numpy.array(ptsa)
                            npb = numpy.array(ptsb)
                            ta = (npa[: , 3] - npa[0 , 3]) / (npa[-1 , 3] - npa[0 , 3])
                            tb = (npb[: , 3] - npb[0 , 3]) / (npb[-1 , 3] - npb[0 , 3])

                            interpolator = scipy.interpolate.make_interp_spline(ta , npa[: , [0 , 1 , 2]] , k = 1)

                            newa = interpolator(tb)

                            newpts = []
                            for i in range(newa.shape[0]):
                                newx = newa[i , 0] * (1.0 - t1) + npb[i , 0] * t1
                                newy = newa[i , 1] * (1.0 - t1) + npb[i , 1] * t1
                                newp = newa[i , 2] * (1.0 - t1) + npb[i , 2] * t1
                                if newx < 0:
                                    newx = 0.0
                                elif newx > 1:
                                    newx = 1.0
                                if newy < 0:
                                    newy = 0.0
                                elif newy > 1.0 / self._ar:
                                    newy = 1.0 / self._ar
                                if newp < 0:
                                    newp = 0.0
                                elif newp > 1:
                                    newp = 1.0
                                newpts.append(
                                        [newx,
                                         newy,
                                         newp,
                                         ptsb[i][3] , ptsb[i][4]]
                                        )
                            color = int(ptsb[0][4]) # todo, instead of parameters
                            color = int(ptsb[0][4]) # todo, instead of parameters
                            thickness , red , green , blue , opacity = self._dark_colors[color]
                            shapes_list_part += draw.simple_stroke_shapes(newpts , 
                                                                    parameters = {
                                                                           "thickness" : thickness , 
                                                                            "color" : (int(red) , int(green) , int(blue)) ,
                                                                            "opacity" : int(opacity)
                                                                            })

                ab = [None , None]
            
        frames.append(frames_before + shapes_list_part)

    frames , reco = self._make_equalish_time(frames , reco)
    return State(before + finalstrokes , {'frames' : frames , 'recording' : reco})

