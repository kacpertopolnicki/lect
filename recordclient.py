import sys
import pickle
import pyglet
import copy
import time
import numpy
import logging
import curses
import os
import PIL
import cv2
import subprocess

from log import logger
import draw
from record import State , Record

RECORD_CLIENT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

class RecordClient:
    def __init__(self , output , record , dark_pallete = "default_pallete" , light_pallete = "default_pallete" , printout = None):

        # OUTPUT

        self._output_file = output

        self._printout = None
        if printout is not None and not os.path.isdir(printout) and not os.path.isfile(printout):
            self._printout = printout
            os.mkdir(self._printout)

        # RECORD

        self._record = record
        self._state_cursor = -1
        self._commands_after = []
        self._commands_after_index = 0

        # CONFIGURATION
        
        self._configuration = record.get_configuration()

        # GEOMETRY

        self._ar = self._configuration["paper"].getfloat("aspectratio")
        self._window_width = self._configuration["window"].getint("width")
        self._window_height = self._configuration["window"].getint("height")
       
        # FRAMES

        self._frame_width = self._configuration["frames"].getint("width")
        self._frame_height = self._configuration["frames"].getint("height")
        self._frame_preview_width = self._configuration["frames"].getint("preview_width")
        self._frame_preview_height = self._configuration["frames"].getint("preview_height")
        self._frame_rate = self._configuration["frames"].getint("frame_rate")
        self._antialias = self._configuration["frames"].getint("antialias")
        self._preview_command = self._configuration["frames"]["preview_command"]
        logger.debug("self._antialias : " + str(self._antialias))

        # COLORS

        self._dark_pallete = dark_pallete
        self._light_pallete = light_pallete
        self._pallete = dark_pallete
        self._set_colors(self._pallete)

        self._color = 1

        logger.debug("self._paper_color = " + str(self._paper_color))
        logger.debug("self._colors = " + str(self._colors))

        # CURRENT STROKE

        self._current_batch = pyglet.graphics.Batch()
        self._current_shapes = []

        # PAPER

        self._paper_batch = pyglet.graphics.Batch()
        self._paper = None
        
        # STROKES

        self._stroke_batches = dict()
        self._stroke_shapes = dict()
        self._stroke_recalculate = False

        # CURSES

        self._curses_screen = curses.initscr()
        self._update_curses_screen()

        # WINDOW
        
        window_config = pyglet.gl.Config(sample_buffers=1, samples=16 , double_buffer = True)
        self._window = pyglet.window.Window(self._window_width , self._window_height,
                                            "record", resizable = True,
                                            config = window_config)
        image = pyglet.image.load(os.path.join(RECORD_CLIENT_DIRECTORY , "resources" , "white_cursor.png"))
        cursor = pyglet.window.ImageMouseCursor(
                image ,
                0 , 0)
        self._window.set_mouse_cursor(cursor)

        @self._window.event
        def on_resize(width , height):
            self._window_width , self._window_height = self._window.get_size()
            self._stroke_recalculate = True
            

        @self._window.event
        def on_draw():
            self._window.clear()
            x0 , y0 , x1 , y1 = self._get_rectangle()

            self._paper_batch = pyglet.graphics.Batch()
            self._paper = pyglet.shapes.Rectangle(
                x0 , y0 , 
                x1 - x0 , 
                y1 - y0 ,
                color = self._paper_color ,
                batch = self._paper_batch)
            self._paper_batch.draw()

            pts = self._record.get_stroke("current")
            if len(pts) >= 2:
                points = [(x0 + x * (x1 - x0) , y0 + y * (x1 - x0)) for (x , y , p , t , c) in pts]
                self._current_batch = pyglet.graphics.Batch()
                multiline = pyglet.shapes.MultiLine(*points , color = (255 , 255 , 255) , batch = self._current_batch)
                self._current_shapes = [multiline]
                self._current_batch.draw()

            current_strokes = self._record.get_current_strokes(cursor = self._state_cursor)

            for s in current_strokes:
                if (s not in self._stroke_batches) or self._stroke_recalculate:
                    logger.debug("Recalculating stroke " + s + ".")
                    pts = self._record.get_stroke(s)
                    
                    color = int(pts[0][4]) # todo, instead of parameters
                    thickness , red , green , blue , opacity = self._colors[color]

                    shapes_list = draw.simple_stroke_shapes(pts , 
                                                            parameters = {
                                                                   "thickness" : thickness , 
                                                                    "color" : (int(red) , int(green) , int(blue)) ,
                                                                    "opacity" : int(opacity)
                                                                    })
                    
                    self._stroke_batches[s] = pyglet.graphics.Batch()
                    self._stroke_shapes[s] = []

                    draw.pyglet_draw_shapes(shapes_list , (x0 , y0 , x1 , y1) , shps = self._stroke_shapes[s] , batch = self._stroke_batches[s])

                    logger.debug(" len(self._stroke_shapes[s]) = " + str(len(self._stroke_shapes[s])))
                    logger.debug(" self._stroke.batches[s] = " + str(self._stroke_batches[s]))
                self._stroke_batches[s].draw()
            self._stroke_recalculate = False

        @self._window.event
        def on_key_release(symbol , modifiers):
            if modifiers == pyglet.window.key.MOD_CTRL:
                if 48 <= symbol <= 57:
                    logger.debug("color number = " + str(int(symbol) - 48) + ".")
                    self._color = int(symbol) - 48
                elif symbol == pyglet.window.key.J:
                    self._state_cursor -= 1
                elif symbol == pyglet.window.key.K:
                    self._state_cursor += 1
                elif symbol == pyglet.window.key.H:
                    self._state_cursor -= 10
                elif symbol == pyglet.window.key.L:
                    self._state_cursor += 10
                elif symbol == pyglet.window.key.D:
                    commands = self._record.modify_after_cursor(self._state_cursor)
                    if commands is not None:
                        self._commands_after = commands 
                        self._commands_after_index = 0
                    self._state_cursor = -1
                elif symbol == pyglet.window.key.X:
                    commands = self._record.modify_after_cursor(self._state_cursor , save_commands = False)
                    if commands is not None:
                        self._commands_after = commands 
                        self._commands_after_index = 0
                    self._state_cursor = -1
                elif symbol == pyglet.window.key.N:
                    if len(self._commands_after) > 0:
                        pos = self._commands_after_index % len(self._commands_after)
                        command = self._commands_after[pos]
                        self._record.change_command(command)
                    self._commands_after_index += 1
                elif symbol == pyglet.window.key.R:
                    if len(self._commands_after) > 0:
                        for i in range(len(self._commands_after)):
                            command = self._commands_after[i]
                            self._record.add_command(command)
                    self._commands_after = []
                    self._commands_after_index = 0
                elif symbol == pyglet.window.key.P:
                    all_frames = self._record.get_frames(cursor = self._state_cursor)

                    antialias = 1
                    if all_frames is not None:

                        fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
                        video = cv2.VideoWriter(
                                self._output_file , 
                                fourcc, 
                                self._frame_rate , 
                                (self._frame_preview_width , self._frame_preview_height)
                                )

                        i = 1
                        for frame in all_frames:
                            self._update_curses_screen("Calculating preview frame " + str(i) + " / " + str(len(all_frames)) + ".")
                            i += 1
                            r , b , g  = self._paper_color
                            a = 255
                            frame_pil = PIL.Image.new(
                                                    mode = "RGBA" , 
                                                    size = (self._frame_preview_width * antialias , self._frame_preview_height * antialias) , 
                                                    color = (r , b , g , a))
                            frame_pil_draw = PIL.ImageDraw.Draw(frame_pil)
                            draw.pil_draw_shapes(
                                    frame_pil_draw ,
                                    frame ,
                                    self._get_rectangle(
                                        size = (antialias * self._frame_preview_width , antialias * self._frame_preview_height)))
                            if antialias != 1:
                                frame_pil = frame_pil.resize((self._frame_preview_width , self._frame_preview_height) , resample = PIL.Image.LANCZOS)
                            video.write(cv2.cvtColor(numpy.array(frame_pil) , cv2.COLOR_RGB2BGR))

                        video.release()
                        subprocess.run(self._preview_command.strip().split() + [self._output_file])
                elif symbol == pyglet.window.key.S:
                    all_frames = self._record.get_all_frames()
                    if len(all_frames) > 0:

                        fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
                        video = cv2.VideoWriter(
                                self._output_file , 
                                fourcc, 
                                self._frame_rate , 
                                (self._frame_width , self._frame_height)
                                )

                        i = 1
                        for frame in all_frames:
                            self._update_curses_screen("Calculating frame " + str(i) + " / " + str(len(all_frames)) + ".")
                            logger.info("Calculating frame " + str(i) + " / " + str(len(all_frames)) + ".")
                            logger.debug("starting ...")
                            i += 1
                            r , b , g  = self._paper_color
                            a = 255
                            logger.debug("PIL.Image.new(...)")
                            frame_pil = PIL.Image.new(
                                                    mode = "RGBA" , 
                                                    size = (self._frame_width * self._antialias , self._frame_height * self._antialias) , 
                                                    color = (r , b , g , a))
                            logger.debug("PIL.ImageDraw.Draw(...)")
                            frame_pil_draw = PIL.ImageDraw.Draw(frame_pil)
                            logger.debug("draw.pil_draw_shapes(...)")
                            draw.pil_draw_shapes(
                                    frame_pil_draw ,
                                    frame ,
                                    self._get_rectangle(
                                        size = (self._antialias * self._frame_width , self._antialias * self._frame_height)))
                            if self._antialias != 1:
                                logger.debug("frame_pil.resize(...)")
                                frame_pil = frame_pil.resize((self._frame_width , self._frame_height) , resample = PIL.Image.LANCZOS)
                            logger.debug("video.write(...)")
                            video.write(cv2.cvtColor(numpy.array(frame_pil) , cv2.COLOR_RGB2BGR))
                            logger.debug("... done")
                        video.release()
                        subprocess.run(self._preview_command.strip().split() + [self._output_file])
                    
                    last_frames = self._record.get_printout_frames()
                    if len(last_frames) > 0 and self._printout is not None:
                        self._set_colors(self._light_pallete)
                        for i in range(len(last_frames)):
                            self._update_curses_screen("Calculating printout frame " + str(i + 1) + " / " + str(len(last_frames)) + ".")
                            logger.info("Calculating printout frame " + str(i + 1) + " / " + str(len(last_frames)) + ".")
                            logger.debug("starting ...")
                            frame = last_frames[i]
                            r , b , g  = self._paper_color
                            a = 255
                            logger.debug("PIL.Image.new(...)")
                            frame_pil = PIL.Image.new(
                                                    mode = "RGBA" , 
                                                    size = (self._frame_width * self._antialias , self._frame_height * self._antialias) , 
                                                    color = (r , b , g , a))
                            logger.debug("PIL.ImageDraw.Draw(...)")
                            frame_pil_draw = PIL.ImageDraw.Draw(frame_pil)
                            logger.debug("draw.pil_draw_shapes(...)")
                            draw.pil_draw_shapes(
                                    frame_pil_draw ,
                                    frame ,
                                    self._get_rectangle(
                                        size = (self._antialias * self._frame_width , self._antialias * self._frame_height)))
                            if self._antialias != 1:
                                logger.debug("frame_pil.resize(...)")
                                frame_pil = frame_pil.resize((self._frame_width , self._frame_height) , resample = PIL.Image.LANCZOS)
                            logger.debug("frame_pil.save(...)")                                
                            frame_pil.save(os.path.join(self._printout , str(i) + ".png"))
                            logger.debug("...done")
                        self._set_colors(self._dark_pallete)
                            
            else:
                if symbol == pyglet.window.key.ENTER:
                    char = '\n'
                    self._record.add_to_command(char)
                    self._state_cursor = -1
                elif symbol == pyglet.window.key.BACKSPACE:
                    char = chr(8)
                    self._record.add_to_command(char)
                    self._state_cursor = -1
                elif 32 <= symbol <= 127:
                    char = chr(symbol)
                    self._record.add_to_command(char)
                    self._state_cursor = -1

            self._update_curses_screen()
     
        # TABLET

        tablets = pyglet.input.get_tablets()
        if len(tablets) > 0:
            self._tablet = tablets[0]
            self._tablet = self._tablet.open(self._window)
        
            @self._tablet.event
            def on_motion(cursor, x, y, pressure, *rest):
                x0 , y0 , x1 , y1 = self._get_rectangle()
                xx = (x - x0) / (x1 - x0)
                yy = (y - y0) / (x1 - x0)
                self._record.add_to_stroke(xx , yy , pressure , time.time() , self._color)

                self._update_curses_screen()
        else:
            raise RuntimeError("No graphics tablet detected.")

    def _set_colors(self , pallete):
        self._paper_color = list(map(int , self._configuration[pallete]["paper_color"].split(",")))

        self._colors =  [
                            list(map(float , self._configuration[pallete][c].split(",")))
                            for c in    ["color_0" , "color_1" , "color_2" , "color_3" , "color_4" ,
                                         "color_5" , "color_6" , "color_7" , "color_8" , "color_9"
                                        ]
                        ]

    def _update_curses_screen(self , string = None):
        height , width = self._curses_screen.getmaxyx()
        self._curses_screen.clear()
        if string is None:
            self._curses_screen.addstr(("command : " + self._record.get_current_command())[:width - 1] + "\n\n" + self._record.nicestr(cursor = self._state_cursor , width = width , height = height))
        else:
            string = string.strip()
            string = string.replace("\n" , " , ")
            string = string[-width:]
            
            self._curses_screen.addstr(string)
        self._curses_screen.refresh()

    def _get_rectangle(self , size = None):
        window_width , window_height = self._window_width , self._window_height
        if size is not None:
            window_width , window_height = size
        if window_width / self._ar <= window_height:
            return (
                        0 , 
                        0.5 * (window_height - (window_width / self._ar)) , 
                        window_width , 
                        0.5 * (window_height - (window_width / self._ar)) + 
                        window_width / self._ar
                    )
        else:
            return (
                        0.5 * (window_width - (self._ar * window_height)) , 
                        0 ,
                        0.5 * (window_width - (self._ar * window_height)) + 
                        (self._ar * window_height) , 
                        window_height)

    def run(self):
        pyglet.app.run()

