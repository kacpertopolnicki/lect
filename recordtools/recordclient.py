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
import pyperclip as pc
import math
import time

from .log import logger
from . import draw
from .record import State , Record

RECORD_CLIENT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

class RecordClient:
    def __init__(self , animation_output , sound_output , record ,
                 gui = True ,
                 dark_pallete = "default_pallete" , 
                 light_pallete = "default_pallete" , 
                 printout = None , pickle_path = None):

        # GUI

        self._gui = gui
        
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
        elif printout is not None:
            self._printout = printout

        # RECORD

        self._record = record
        self._state_cursor = -1
        self._commands_after = []
        self._commands_after_index = 0

        # PICKLE

        self._pickle_path = pickle_path

        # CONFIGURATION
        
        self._configuration = record.get_configuration()

        # CTRL KEYS

        self._preview_audio = self._configuration["ctrlkeys"]["preview_audio"].strip()
        self._preview_video = self._configuration["ctrlkeys"]["preview_video"].strip()
        self._preview_save = self._configuration["ctrlkeys"]["preview_save"].strip()
        self._save = self._configuration["ctrlkeys"]["save"].strip()
        self._sound_record = self._configuration["ctrlkeys"]["sound_record"].strip()
        self._write_pickle = self._configuration["ctrlkeys"]["write_pickle"].strip()
        self._paste_image = self._configuration["ctrlkeys"]["paste_image"].strip()
        self._cursor_up = self._configuration["ctrlkeys"]["cursor_up"].strip()
        self._cursor_down = self._configuration["ctrlkeys"]["cursor_down"].strip()
        self._cursor_up_10 = self._configuration["ctrlkeys"]["cursor_up_10"].strip()
        self._cursor_down_10 = self._configuration["ctrlkeys"]["cursor_down_10"].strip()
        self._delete_save = self._configuration["ctrlkeys"]["delete_save"].strip()
        self._delete_no_save = self._configuration["ctrlkeys"]["delete_no_save"].strip()
        self._rerun_commands = self._configuration["ctrlkeys"]["rerun_commands"].strip()
        self._grid_onoff = self._configuration["ctrlkeys"]["grid_onoff"].strip()
        
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
        self._background_pause = self._configuration["frames"].getint("background_pause")

        # COLORS

        self._dark_pallete = dark_pallete
        self._light_pallete = light_pallete
        self._pallete = dark_pallete
        self._set_colors(self._pallete)

        self._color = 1

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
        self._sprites = dict()
        self._stroke_shapes = dict()
        self._stroke_recalculate = False

        # CURSES

        self._status = None
        self._curses_screen = None
        if self._gui:
            self._curses_screen = curses.initscr()
            curses.curs_set(0) 
            self._update_curses_screen()

        # GRID

        self._grid_batch = pyglet.graphics.Batch()
        self._grid_shapes = []

        self._grid1_batch = pyglet.graphics.Batch()
        self._grid1_shapes = []

        self._grid2_batch = pyglet.graphics.Batch()
        self._grid2_shapes = []

        self._grid3_batch = pyglet.graphics.Batch()
        self._grid3_shapes = []

        self._grid_types = [None , self._grid_batch , self._grid1_batch , self._grid2_batch , self._grid3_batch]

        self._grid_shapes_n = self._configuration["grid"].getint("grid_lines")
        self._grid_color = list(map(int , self._configuration["grid"]["grid_color"].split(",")))
        self._grid_on = 0

        # WINDOW
       
        if self._gui:
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

                #self._set_colors(self._dark_pallete)
                r , g , b  = self._paper_color

                self._paper_batch = pyglet.graphics.Batch()
                self._paper = pyglet.shapes.Rectangle(
                    x0 , y0 , 
                    x1 - x0 , 
                    y1 - y0 ,
                    color = self._paper_color ,
                    batch = self._paper_batch)
                self._paper_batch.draw()

                if self._stroke_recalculate:
                    self._grid_batch = pyglet.graphics.Batch()
                    self._grid_shapes = []
                    d = (x1 - x0) / self._grid_shapes_n
                    x = x0 + d
                    while x < x1:
                        lx0 , ly0 = x , y0
                        lx1 , ly1 = x , y1
                        lns = pyglet.shapes.MultiLine((lx0 , ly0) , (lx1 , ly1) , color = self._grid_color , batch = self._grid_batch)
                        self._grid_shapes.append(lns)
                        x += d
                    y = y0 + 0.5 * (y1 - y0) + 0.5 * d
                    while y < y1:
                        lx0 , ly0 = x0 , y
                        lx1 , ly1 = x1 , y
                        lns = pyglet.shapes.MultiLine((lx0 , ly0) , (lx1 , ly1) , color = self._grid_color , batch = self._grid_batch)
                        self._grid_shapes.append(lns)
                        y += d
                    y = y0 + 0.5 * (y1 - y0) - 0.5 * d
                    while y > y0:
                        lx0 , ly0 = x0 , y
                        lx1 , ly1 = x1 , y
                        lns = pyglet.shapes.MultiLine((lx0 , ly0) , (lx1 , ly1) , color = self._grid_color , batch = self._grid_batch)
                        self._grid_shapes.append(lns)
                        y -= d
                    c = pyglet.shapes.Circle(0.5 * (x0 + x1) , 0.5 * (y0 + y1) , 3 , color = self._grid_color , batch = self._grid_batch)
                    self._grid_shapes.append(c)

                    self._grid1_batch = pyglet.graphics.Batch()
                    self._grid1_shapes = []
                    for x in numpy.linspace(x0 , x1 , 4):
                        lx0 , ly0 = x , y0
                        lx1 , ly1 = x , y1
                        lns = pyglet.shapes.MultiLine((lx0 , ly0) , (lx1 , ly1) , color = self._grid_color , batch = self._grid1_batch)
                        self._grid1_shapes.append(lns)
                    for y in numpy.linspace(y0 , y1 , 4):
                        lx0 , ly0 = x0 , y
                        lx1 , ly1 = x1 , y
                        lns = pyglet.shapes.MultiLine((lx0 , ly0) , (lx1 , ly1) , color = self._grid_color , batch = self._grid1_batch)
                        self._grid1_shapes.append(lns)
                    c = pyglet.shapes.Circle(0.5 * (x0 + x1) , 0.5 * (y0 + y1) , 3 , color = self._grid_color , batch = self._grid1_batch)
                    self._grid1_shapes.append(c)

                    self._grid2_batch = pyglet.graphics.Batch()
                    self._grid2_shapes = []
                    for x in numpy.linspace(x0 , x1 , 5):
                        lx0 , ly0 = x , y0
                        lx1 , ly1 = x , y1
                        lns = pyglet.shapes.MultiLine((lx0 , ly0) , (lx1 , ly1) , color = self._grid_color , batch = self._grid2_batch)
                        self._grid2_shapes.append(lns)
                    for y in numpy.linspace(y0 , y1 , 5):
                        lx0 , ly0 = x0 , y
                        lx1 , ly1 = x1 , y
                        lns = pyglet.shapes.MultiLine((lx0 , ly0) , (lx1 , ly1) , color = self._grid_color , batch = self._grid2_batch)
                        self._grid2_shapes.append(lns)
                    
                    c = pyglet.shapes.Circle(0.5 * (x0 + x1) , 0.5 * (y0 + y1) , 3 , color = self._grid_color , batch = self._grid2_batch)
                    self._grid2_shapes.append(c)

                    self._grid3_batch = pyglet.graphics.Batch()
                    self._grid3_shapes = []
                    dx = (x1 - x0) / self._grid_shapes_n
                    x = x0 - 2 * int((x1 - x0) / dx) * dx
                    while x < x1 + 2 * (x1 - x0): 
                        px0 , py0 = x , 0.5 * (y0 + y1)
                        lx0 , ly0 = x0 , py0 + (x - x0) * math.tan(math.pi / 6.0)
                        lx1 , ly1 = x1 , py0 - (x1 - x) * math.tan(math.pi / 6.0)
                        if ly0 > y1:
                            lx0 , ly0 = px0 - 0.5 * (y1 - y0) / math.tan(math.pi / 6.0) , y1
                        if ly1 < y0:
                            lx1 , ly1 = px0 + 0.5 * (y1 - y0) / math.tan(math.pi / 6.0) , y0

                        lns = pyglet.shapes.MultiLine((lx0 , ly0) , (lx1 , ly1) , color = self._grid_color , batch = self._grid3_batch)
                        self._grid3_shapes.append(lns)
                        x += dx
                    
                    x = x0 - 2 * int((x1 - x0) / dx) * dx
                    while x < x1 + 2 * (x1 - x0): 
                        px0 , py0 = x , 0.5 * (y0 + y1)
                        lx0 , ly0 = x0 , py0 - (x - x0) * math.tan(math.pi / 6.0)
                        lx1 , ly1 = x1 , py0 + (x1 - x) * math.tan(math.pi / 6.0)
                        if ly0 < y0:
                            lx0 , ly0 = px0 - 0.5 * (y1 - y0) / math.tan(math.pi / 6.0) , y0
                        if ly1 > y1:
                            lx1 , ly1 = px0 + 0.5 * (y1 - y0) / math.tan(math.pi / 6.0) , y1

                        lns = pyglet.shapes.MultiLine((lx0 , ly0) , (lx1 , ly1) , color = self._grid_color , batch = self._grid3_batch)
                        self._grid3_shapes.append(lns)
                        x += dx
                    
                    x = x0 + dx
                    while x < x1: 
                        lx0 , ly0 = x , y0
                        lx1 , ly1 = x , y1

                        lns = pyglet.shapes.MultiLine((lx0 , ly0) , (lx1 , ly1) , color = self._grid_color , batch = self._grid3_batch)
                        self._grid3_shapes.append(lns)
                        x += dx / 2
                    
                    c = pyglet.shapes.Circle(0.5 * (x0 + x1) , 0.5 * (y0 + y1) , 3 , color = self._grid_color , batch = self._grid3_batch)
                    self._grid3_shapes.append(c)

                    self._grid_types = [None , self._grid_batch , self._grid1_batch , self._grid2_batch , self._grid3_batch]

                grid_batch = self._grid_types[self._grid_on]
                if grid_batch is not None:
                    grid_batch.draw()

                pts = self._record.get_stroke("current")
                if len(pts) >= 2:
                    points = [(x0 + x * (x1 - x0) , y0 + y * (x1 - x0)) for (x , y , p , t , c) in pts]
                    self._current_batch = pyglet.graphics.Batch()
                    multiline = pyglet.shapes.MultiLine(*points , color = (255 , 255 , 255) , batch = self._current_batch)
                    self._current_shapes = [multiline]
                    self._current_batch.draw()
        
                current_strokes = self._record.get_current_strokes_images(cursor = self._state_cursor)

                for s in current_strokes:
                    if (s not in self._stroke_batches) or self._stroke_recalculate:
                        t = self._record.get_type(s)
                        if t is not None and t == "stroke":
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

                            draw.pyglet_draw_shapes(shapes_list , (x0 , y0 , x1 , y1) , shps = self._stroke_shapes[s] , batch = self._stroke_batches[s] , background = (r , g , b))

                        elif t is not None and t == "image":
                            logger.debug("Recalculating image " + s + ".")
                            img = self._record.get_image(s)
                            shapes_list = [img]
                            self._stroke_batches[s] = pyglet.graphics.Batch()
                            self._stroke_shapes[s] = []
                            draw.pyglet_draw_shapes(shapes_list , (x0 , y0 , x1 , y1) , shps = self._stroke_shapes[s] , batch = self._stroke_batches[s] , background = (r , g , b))
                    self._stroke_batches[s].draw()
                self._stroke_recalculate = False

            @self._window.event
            def on_key_release(symbol , modifiers):
                if modifiers == pyglet.window.key.MOD_CTRL:
                    if 48 <= symbol <= 57:
                        self._color = int(symbol) - 48
                    #elif symbol == pyglet.window.key.J:
                    elif symbol == ord(self._cursor_down):
                        self._state_cursor -= 1
                    #elif symbol == pyglet.window.key.K:
                    elif symbol == ord(self._cursor_up):
                        self._state_cursor += 1
                    #elif symbol == pyglet.window.key.H:
                    elif symbol == ord(self._cursor_down_10):
                        self._state_cursor -= 10
                    #elif symbol == pyglet.window.key.L:
                    elif symbol == ord(self._cursor_up_10):
                        self._state_cursor += 10
                    elif symbol == ord(self._grid_onoff):
                        self._grid_on += 1
                        self._grid_on = self._grid_on % len(self._grid_types)
                    #elif symbol == pyglet.window.key.D:
                    elif symbol == ord(self._delete_save):
                        commands = self._record.modify_after_cursor(self._state_cursor)
                        if commands is not None:
                            self._commands_after = commands 
                            self._commands_after_index = 0
                        self._state_cursor = -1
                        self._record.reexecute(cursor = self._state_cursor)
                    #elif symbol == pyglet.window.key.X:
                    elif symbol == ord(self._delete_no_save):
                        commands = self._record.modify_after_cursor(self._state_cursor , save_commands = False)
                        if commands is not None:
                            self._commands_after = commands 
                            self._commands_after_index = 0
                        self._state_cursor = -1
                        self._record.reexecute(cursor = self._state_cursor)
                    #elif symbol == pyglet.window.key.R:
                    elif symbol == ord(self._rerun_commands):
                        if len(self._commands_after) > 0:
                            for i in range(len(self._commands_after)):
                                command = self._commands_after[i]
                                self._status = "Executing command : " + command
                                self._update_curses_screen()
                                self._record.add_command(command)
                        self._commands_after = []
                        self._commands_after_index = 0
                        self._status = None
                    #elif symbol == pyglet.window.key.O:
                    elif symbol == ord(self._preview_audio): # todo this might not work in the future
                        logger.debug("Calculating audio.")

                        additional = self._record.get_frames(cursor = self._state_cursor)
                        
                        if additional is not None and "recording" in additional:
                            all_recordings = []
                            i_printout = [1]

                            self._calculate_frames(additional , None , all_recordings , 
                                              None , None ,
                                              len(additional["frames"]) , -1 ,
                                              resolution = (self._frame_preview_width , self._frame_preview_height) , antialias = 1 , 
                                              animation = False , audio = True , printout = False)

                            filepath = os.path.join(RECORD_CLIENT_DIRECTORY , "temporary.wav")
                            all_recordings = numpy.concatenate(all_recordings)
                            with wave.open(filepath, 'wb') as wf:
                                wf.setnchannels(self._channels)
                                wf.setsampwidth(numpy.dtype(self._dtype).itemsize)
                                wf.setframerate(self._samplerate)
                                wf.writeframes(all_recordings.tobytes())
                            subprocess.run(self._sound_preview_command.strip().split() + [filepath])

                        self._status = None
                    #elif symbol == pyglet.window.key.P:
                    elif symbol == ord(self._preview_video): # todo this might not work in the future
                        logger.debug("Calculating preview.")

                        additional = self._record.get_frames(cursor = self._state_cursor)
                        
                        if additional is not None and "frames" in additional:
                            try:
                                filepath = os.path.join(RECORD_CLIENT_DIRECTORY , "temporary.mp4")

                                fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
                                video = cv2.VideoWriter(
                                        filepath , 
                                        fourcc, 
                                        self._frame_rate , 
                                        (self._frame_preview_width , self._frame_preview_height)
                                        )

                                all_recordings = []
                                i_frame = [1]
                                i_printout = [1]

                                self._calculate_frames(additional , video , all_recordings , 
                                                  i_frame , i_printout ,
                                                  len(additional["frames"]) , -1 ,
                                                  resolution = (self._frame_preview_width , self._frame_preview_height) , antialias = 1 , 
                                                  animation = True , audio = False , printout = False)

                            except Exception as e:
                                video.release()
                                subprocess.run(self._preview_command.strip().split() + [filepath])
                                raise e
                            finally:
                                video.release()
                                subprocess.run(self._preview_command.strip().split() + [filepath])

                        self._status = None
                    #elif symbol == pyglet.window.key.A:
                    elif symbol == ord(self._preview_save):
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
                                    (self._frame_preview_width , self._frame_preview_height)
                                    )

                            all_recordings = []
                            i_frame = [1]
                            i_printout = [1]

                            for aa in all_additional:
                                self._calculate_frames(aa , video , all_recordings,
                                                       i_frame , i_printout,
                                                       len_all_frames , len_all_printout,
                                                       resolution = (self._frame_preview_width , self._frame_preview_height), 
                                                       antialias = 1)

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
                    #elif symbol == pyglet.window.key.S:
                    elif symbol == ord(self._save):
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
                            i_frame = [1]
                            i_printout = [1]

                            for aa in all_additional:
                                self._calculate_frames(aa , video , all_recordings,
                                                       i_frame , i_printout,
                                                       len_all_frames , len_all_printout,
                                                       resolution = (self._frame_width , self._frame_height), 
                                                       antialias = self._antialias)

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
                        
                    #elif symbol == pyglet.window.key.G:
                    elif symbol == ord(self._sound_record):
                        if not self._record_sound:
                            logger.debug("Starting recording.")
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
                            logger.debug("Ending recording.")
                            self._status = "ending recording"
                            self._update_curses_screen()
                            self._is.stop()
                            self._is.close()
                            self._is = None
                            self._record_sound = False
                            self._recorded_sound_frames = numpy.concatenate(self._recorded_sound_frames)
                            self._record.add_sound(self._recorded_sound_frames)
                            self._recorded_sound_frames = []
                            self._status = None
                    #elif symbol == pyglet.window.key.W:
                    elif symbol == ord(self._write_pickle):
                        logger.debug("Saving to " + str(self._pickle_path) + ".")
                        if self._pickle_path is not None:
                            with open(self._pickle_path , "wb") as f:
                                pickle.dump(self._record , f)
                    #elif symbol == pyglet.window.key.I:
                    elif symbol == ord(self._paste_image):
                        path = pc.paste()
                        if path is not None and os.path.isfile(path):
                            logger.debug("Adding image: " + path + ".")
                            image = cv2.imread(path)
                            if image is not None:
                                self._record.add_image(image)
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

    def calculate_save(self):
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
            i_frame = [1]
            i_printout = [1]

            for aa in all_additional:
                self._calculate_frames(aa , video , all_recordings,
                                       i_frame , i_printout,
                                       len_all_frames , len_all_printout,
                                       resolution = (self._frame_width , self._frame_height), 
                                       antialias = self._antialias)

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

    def _calculate_frames(self , additional , video , recordings , 
                          i_frame , i_printout ,
                          len_all_frames , len_all_printout ,
                          resolution = None , antialias = None , 
                          animation = True , audio = True , printout = True):

        w_small , h_small = self._frame_width , self._frame_height
        if resolution is not None:
            w_small , h_small = resolution
        aa = self._antialias
        if antialias is not None:
            aa = antialias
        w_large , h_large = w_small * aa , h_small * aa

        if "frames" in additional and animation:
            self._set_colors(self._dark_pallete)
            frames = additional["frames"]
            for frame in frames:
                self._status = "Calculating frame " + str(i_frame[0]) + " / " + str(len_all_frames) + "."
                self._update_curses_screen()
                logger.info("Calculating frame " + str(i_frame[0]) + " / " + str(len_all_frames) + ".")
                r , g , b  = self._paper_color
                a = 255
                frame_pil = PIL.Image.new(
                                        mode = "RGB" , 
                                        size = (w_large , h_large) , 
                                        color = (r , g , b))
                frame_pil_draw = PIL.ImageDraw.Draw(frame_pil)
                draw.pil_draw_shapes(
                        frame_pil ,
                        frame_pil_draw ,
                        frame ,
                        self._get_rectangle(
                            size = (w_large , h_large)) , background = (r , g , b))
                if aa != 1:
                    frame_pil = frame_pil.resize((w_small , h_small) , resample = PIL.Image.LANCZOS)
                video.write(cv2.cvtColor(numpy.array(frame_pil) , cv2.COLOR_RGB2BGR))
                i_frame[0] += 1
        if "printout" in additional and printout:
            if self._printout is not None:
                if not os.path.isdir(self._printout):
                    os.mkdir(self._printout)
                self._set_colors(self._light_pallete)
                frame = additional["printout"]
                self._status = "Calculating printout frame " + str(i_printout[0]) + " / " + str(len_all_printout) + "."
                self._update_curses_screen()
                logger.info("Calculating printout frame " + str(i_printout[0]) + " / " + str(len_all_printout) + ".")
                r , g , b  = self._paper_color
                a = 255
                frame_pil = PIL.Image.new(
                                        mode = "RGB" , 
                                        size = (w_large , h_large) , 
                                        color = (r , g , b))
                frame_pil_draw = PIL.ImageDraw.Draw(frame_pil)
                draw.pil_draw_shapes(
                        frame_pil ,
                        frame_pil_draw ,
                        frame ,
                        self._get_rectangle(
                            size = (w_large , h_large)) , background = (r , g , b))
                if aa != 1:
                    frame_pil = frame_pil.resize((w_small , h_small) , resample = PIL.Image.LANCZOS)
                path = os.path.join(self._printout , str(i_printout[0]) + ".png")
                frame_pil.save(path)
                i_printout[0] += 1
        if "recording" in additional and audio:
            recordings.append(additional["recording"])
        self._set_colors(self._dark_pallete)
        self._status = None


    def _set_colors(self , pallete):
        self._paper_color = list(map(int , self._configuration[pallete]["paper_color"].split(",")))

        self._colors =  [
                            list(map(float , self._configuration[pallete][c].split(",")))
                            for c in    ["color_0" , "color_1" , "color_2" , "color_3" , "color_4" ,
                                         "color_5" , "color_6" , "color_7" , "color_8" , "color_9"
                                        ]
                        ]

    def _update_curses_screen(self):
        if self._gui:
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
        else:
            if self._status is not None:
                string = copy.deepcopy(self._status)
                string = string.strip()

                sys.stdout.write(string + "\n")

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
        if self._gui:
            pyglet.app.run()

