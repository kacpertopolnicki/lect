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
import sounddevice as sd
import wave
import tempfile

from log import logger
import draw
from record import State , Record

import time

RECORD_CLIENT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

class RecordClient:
    def __init__(self , animation_output , sound_output , record ,
                 dark_pallete = "default_pallete" , 
                 light_pallete = "default_pallete" , 
                 printout = None , pickle_path = None):

        # OUTPUT

        self._output_file = animation_output
        if (os.path.isdir(animation_output) or os.path.isfile(animation_output)):
            raise ValueError("Animation output path exists.")

        self._audiopath = sound_output
        if (os.path.isdir(sound_output) or os.path.isfile(sound_output)):
            raise ValueError("Sound output path exists.")

        self._printout = None
        if printout is not None and (os.path.isdir(printout) or os.path.isfile(printout)):
            raise ValueError("Printout directory exists.")
        if printout is not None:
            self._printout = printout
            os.mkdir(self._printout)

        # RECORD

        self._record = record
        self._state_cursor = -1
        self._commands_after = []
        self._commands_after_index = 0

        # PICKLE

        self._pickle_path = pickle_path

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

        # SOUND

        self._output_device = self._configuration["sound"]["output_device"]
        self._input_device = self._configuration["sound"]["input_device"]
        # sauce : https://pythonfriday.dev/2025/07/289-record-audio-with-sounddevice/
        self._samplerate = self._configuration["sound"].getint("sample_rate")
        self._channels = self._configuration["sound"].getint("channels")
        self._sound_preview_command = self._configuration["sound"]["sound_preview_command"]
        self._dtype = 'int16'
        self._record_sound = False
        self._recorded_sound_frames = []

        def callback(indata , frames , time , status):
            self._recorded_sound_frames.append(indata.copy())

        self._callback = callback
        self._is = None

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

        self._status = None
        self._curses_screen = curses.initscr()
        curses.curs_set(0) 
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
                    self._record.reexecute(cursor = self._state_cursor)
                elif symbol == pyglet.window.key.X:
                    commands = self._record.modify_after_cursor(self._state_cursor , save_commands = False)
                    if commands is not None:
                        self._commands_after = commands 
                        self._commands_after_index = 0
                    self._state_cursor = -1
                    self._record.reexecute(cursor = self._state_cursor)
                elif symbol == pyglet.window.key.R:
                    if len(self._commands_after) > 0:
                        for i in range(len(self._commands_after)):
                            command = self._commands_after[i]
                            self._record.add_command(command)
                    self._commands_after = []
                    self._commands_after_index = 0
                elif symbol == pyglet.window.key.P:
                    logger.debug("calculating preview")

                    additional = self._record.get_frames(cursor = self._state_cursor)

                    if additional is not None and "frames" in additional:

                        all_frames = additional["frames"]

                        antialias = 1
                        if all_frames is not None:
                            try:
                                filepath = os.path.join(RECORD_CLIENT_DIRECTORY , "temporary.mp4")

                                fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
                                video = cv2.VideoWriter(
                                        filepath , 
                                        fourcc, 
                                        self._frame_rate , 
                                        (self._frame_preview_width , self._frame_preview_height)
                                        )

                                i = 1
                                for frame in all_frames:
                                    self._set_colors(self._dark_pallete)
                                    self._status = "Calculating preview frame " + str(i) + " / " + str(len(all_frames)) + "."
                                    self._update_curses_screen()
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
                            except Exceptions as e:
                                video.release()
                                subprocess.run(self._preview_command.strip().split() + [filepath])
                                raise e
                            finally:
                                video.release()
                                subprocess.run(self._preview_command.strip().split() + [filepath])
                        if "recording" in additional:
                            filepath = os.path.join(RECORD_CLIENT_DIRECTORY , "temporary.wav")
                            frames = additional["recording"]
                            with wave.open(filepath, 'wb') as wf:
                                wf.setnchannels(self._channels)
                                wf.setsampwidth(numpy.dtype(self._dtype).itemsize)
                                wf.setframerate(self._samplerate)
                                wf.writeframes(frames.tobytes())
                            subprocess.run(self._sound_preview_command.strip().split() + [filepath])

                    self._status = None
                elif symbol == pyglet.window.key.A:
                    all_additional = self._record.get_all_additional()

                    antialias = 1
                    
                    len_all_frames = 0
                    len_all_printout = 0
                    for a in all_additional:
                        if 'frames' in a:
                            len_all_frames += len(a["frames"])
                        if 'printout' in a:
                            len_all_printout += 1
                    try:
                        fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
                        video = cv2.VideoWriter(
                                self._output_file , 
                                fourcc, 
                                self._frame_rate , 
                                (self._frame_preview_width , self._frame_preview_height)
                                )

                        all_recordings = []
                        i_frame = 1
                        i_printout = 1
                        for aa in all_additional:
                            if "frames" in aa:
                                self._set_colors(self._dark_pallete)
                                frames = aa["frames"]
                                for frame in frames:
                                    self._status = "Calculating frame " + str(i_frame) + " / " + str(len_all_frames) + "."
                                    self._update_curses_screen()
                                    logger.info("Calculating frame " + str(i_frame) + " / " + str(len_all_frames) + ".")
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
                                    if self._antialias != 1:
                                        frame_pil = frame_pil.resize((self._frame_preview_width , self._frame_preview_height) , resample = PIL.Image.LANCZOS)
                                    video.write(cv2.cvtColor(numpy.array(frame_pil) , cv2.COLOR_RGB2BGR))
                                    i_frame += 1
                            if "printout" in aa:
                                self._set_colors(self._light_pallete)
                                self._status = "Calculating printout frame " + str(i_printout) + " / " + str(len_all_printout) + "."
                                self._update_curses_screen()
                                logger.info("Calculating printout frame " + str(i_printout) + " / " + str(len_all_printout) + ".")
                                frame = aa["printout"]
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
                                if self._antialias != 1:
                                    logger.debug("frame_pil.resize(...)")
                                    frame_pil = frame_pil.resize((self._frame_preview_width , self._frame_preview_height) , resample = PIL.Image.LANCZOS)
                                logger.debug(self._printout)
                                logger.debug(str(i_printout))
                                path = os.path.join(self._printout , str(i_printout) + ".png")
                                logger.debug("path : " + str(path))
                                logger.debug("frame_pil : " + str(frame_pil))
                                frame_pil.save(path)
                                i_printout += 1
                            if "recording" in aa:
                                all_recordings.append(aa["recording"])

                        all_recordings = numpy.concatenate(all_recordings)
                        with wave.open(self._audiopath, 'wb') as wf:
                            wf.setnchannels(self._channels)
                            wf.setsampwidth(numpy.dtype(self._dtype).itemsize)
                            wf.setframerate(self._samplerate)
                            wf.writeframes(all_recordings.tobytes())

                    except Exception as e:
                        video.release()
                        raise e
                    finally:
                        video.release()
                    self._status = None

                elif symbol == pyglet.window.key.S:
                    all_additional = self._record.get_all_additional()

                    len_all_frames = 0
                    len_all_printout = 0
                    for a in all_additional:
                        if 'frames' in a:
                            len_all_frames += len(a["frames"])
                        if 'printout' in a:
                            len_all_printout += 1
                    try:
                        fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
                        video = cv2.VideoWriter(
                                self._output_file , 
                                fourcc, 
                                self._frame_rate , 
                                (self._frame_width , self._frame_height)
                                )

                        all_recordings = []
                        i_frame = 1
                        i_printout = 1
                        for aa in all_additional:
                            if "frames" in aa:
                                self._set_colors(self._dark_pallete)
                                frames = aa["frames"]
                                for frame in frames:
                                    self._status = "Calculating frame " + str(i_frame) + " / " + str(len_all_frames) + "."
                                    self._update_curses_screen()
                                    logger.info("Calculating frame " + str(i_frame) + " / " + str(len_all_frames) + ".")
                                    r , b , g  = self._paper_color
                                    a = 255
                                    frame_pil = PIL.Image.new(
                                                            mode = "RGBA" , 
                                                            size = (self._frame_width * self._antialias , self._frame_height * self._antialias) , 
                                                            color = (r , b , g , a))
                                    frame_pil_draw = PIL.ImageDraw.Draw(frame_pil)
                                    draw.pil_draw_shapes(
                                            frame_pil_draw ,
                                            frame ,
                                            self._get_rectangle(
                                                size = (self._antialias * self._frame_width , self._antialias * self._frame_height)))
                                    if self._antialias != 1:
                                        frame_pil = frame_pil.resize((self._frame_width , self._frame_height) , resample = PIL.Image.LANCZOS)
                                    video.write(cv2.cvtColor(numpy.array(frame_pil) , cv2.COLOR_RGB2BGR))
                                    i_frame += 1
                            if "printout" in aa:
                                self._set_colors(self._light_pallete)
                                self._status = "Calculating printout frame " + str(i_printout) + " / " + str(len_all_printout) + "."
                                self._update_curses_screen()
                                logger.info("Calculating printout frame " + str(i_printout) + " / " + str(len_all_printout) + ".")
                                frame = aa["printout"]
                                r , b , g  = self._paper_color
                                a = 255
                                frame_pil = PIL.Image.new(
                                                        mode = "RGBA" , 
                                                        size = (self._frame_width * self._antialias , self._frame_height * self._antialias) , 
                                                        color = (r , b , g , a))
                                frame_pil_draw = PIL.ImageDraw.Draw(frame_pil)
                                draw.pil_draw_shapes(
                                        frame_pil_draw ,
                                        frame ,
                                        self._get_rectangle(
                                            size = (self._antialias * self._frame_width , self._antialias * self._frame_height)))
                                if self._antialias != 1:
                                    logger.debug("frame_pil.resize(...)")
                                    frame_pil = frame_pil.resize((self._frame_width , self._frame_height) , resample = PIL.Image.LANCZOS)
                                logger.debug(self._printout)
                                logger.debug(str(i_printout))
                                path = os.path.join(self._printout , str(i_printout) + ".png")
                                logger.debug("path : " + str(path))
                                logger.debug("frame_pil : " + str(frame_pil))
                                frame_pil.save(path)
                                i_printout += 1
                            if "recording" in aa:
                                all_recordings.append(aa["recording"])

                        all_recordings = numpy.concatenate(all_recordings)
                        with wave.open(self._audiopath, 'wb') as wf:
                            wf.setnchannels(self._channels)
                            wf.setsampwidth(numpy.dtype(self._dtype).itemsize)
                            wf.setframerate(self._samplerate)
                            wf.writeframes(all_recordings.tobytes())

                    except Exception as e:
                        video.release()
                        raise e
                    finally:
                        video.release()
                    self._status = None
                    
                elif symbol == pyglet.window.key.G:
                    if not self._record_sound:
                        logger.debug("starting recording")
                        self._status = "starting recording"
                        self._update_curses_screen()
                        # sauce
                        self._is = sd.InputStream(samplerate = self._samplerate,
                                                  channels = self._channels,
                                                  dtype = self._dtype,
                                                  callback = self._callback, device = self._input_device)
                        self._is.start()
                        self._record_sound = True
                    else:
                        logger.debug("ending recording")
                        self._status = "ending recording"
                        self._update_curses_screen()
                        self._is.stop()
                        self._is.close()
                        self._is = None
                        self._record_sound = False
                        self._recorded_sound_frames = numpy.concatenate(self._recorded_sound_frames)
                        self._record.add_sound(self._recorded_sound_frames)
                        logger.debug("done " + str(self._recorded_sound_frames.shape))
                        self._recorded_sound_frames = []
                        self._status = None
                elif symbol == pyglet.window.key.W:
                    logger.debug("saving" + str(self._pickle_path))
                    if self._pickle_path is not None:
                        with open(self._pickle_path , "wb") as f:
                            pickle.dump(self._record , f)
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

        tablets = pyglet.input.get_tablets()
        if len(tablets) > 0:
            self._tablet = tablets[0]
            self._tablet = self._tablet.open(self._window)
        
            @self._tablet.event
            def on_motion(cursor, x, y, pressure, *rest):
                x0 , y0 , x1 , y1 = self._get_rectangle()
                xx = (x - x0) / (x1 - x0)
                yy = (y - y0) / (x1 - x0)

                l = len(self._record)
                self._record.add_to_stroke(xx , yy , pressure , time.time() , self._color)

                if len(self._record) != l:
                    self._update_curses_screen()
        else:
            raise RuntimeError("No graphics tablet detected.")

    def clean(self):
        if self._is is not None:
            self._is.stop()
            self._is.close()

    def _set_colors(self , pallete):
        self._paper_color = list(map(int , self._configuration[pallete]["paper_color"].split(",")))

        self._colors =  [
                            list(map(float , self._configuration[pallete][c].split(",")))
                            for c in    ["color_0" , "color_1" , "color_2" , "color_3" , "color_4" ,
                                         "color_5" , "color_6" , "color_7" , "color_8" , "color_9"
                                        ]
                        ]

    def _update_curses_screen(self):
        height , width = self._curses_screen.getmaxyx()
        self._curses_screen.clear()
        if self._status is None:
            self._curses_screen.addstr(("          " + 
                        self._record.get_current_command())[:width - 10] + "\n\n" + 
                        self._record.nicestr(cursor = self._state_cursor , 
                                             width = width - 2 , height = height , 
                                             additional = list(map(lambda x : "          [" + x + "]" , self._commands_after))))
        else:
            string = copy.deepcopy(self._status)
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

