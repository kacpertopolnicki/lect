# lect

A simple recorder for lectures and presentations.
Currently in early stages of development. 

Traditionally, information in technical subjects (mathematics, physics, ...)
was shared using chalk and a blackboard. This simple medium is surprisingly
efficient and *lect* is a modern take on this approach. 

# installation

Use at your own risk!

Suggested installation method under:

1) Create a new python environment,
2) Activate this environment,
3) Install requirements using `pip`,
4) Run `lect -h` for help information,
5) Deactivate environment after you are done working with lect.

On linux this process typically looks like the following:

1) First, navigate to a directory where the new environment,
   for example `lectenv` will be saved.
3) A new environment can be created using
```
$ python -m venv lectenv
```
4) The `lectenv` environment can be activated by running:
```
$ . ./lectenv/bin/activate
```
5) Navigate to the directory with the `lect` script.
6) Help information is available from the script:
```
$ . ./lect -h
```
7) To deactivate the environment:
```
$ deactivate
```

# usage

Use at your own risk!

The `lect` script is intended to run from a terminal, and uses
the `curses` library to write out the states of the 
program. After starting `lect` using the following command:
```
$ /path/to/lect temp.mp4 temp.wav -p temp_printout -s temp.pickle
```
the user will be presented with two windows:
![](https://github.com/kacpertopolnicki/lect/blob/main/readme_resources/sc.png)
The smaller one is the terminal, and the larger one is
for graphics tablet input. Additionally:
- the video and audio output will be written to `temp.mp4` and `temp.wav`,
- the printout images will be written to the
  `temp_printout` directory, 
- after hitting ESCAPE to terminate the program
  it's whole state will be pickled to `temp.pickle`.

Each line of the output in the terminal represents a single state of the program. 
For example, after some work with `lect`, the terminal may show:
```
0
          [s_0]
          s_0 [s_1]
          s_0-s_1 [s_2]
          s_0-s_2 [s_3]
          s_0-s_3 [s_4]
          s_0-s_4 [s_5]
          s_0-s_5 [s_6]
          s_0-s_6 [s_7]
          s_0-s_7 [s_8]
          s_0-s_8 [center]
          s_9-s_17
          s_9-s_17 [show]
|  @
```
In the first column:
- `0` marks the beginning of the program,
- `|` marks the current position of the cursor.
In the next column:
- `@` marks that there is some audio and video date associated with a state.
The following columns contain the stack for each state. The stack can be empty,
can contain strokes created by the user using a graphics tablet (`s_0-s_8` means strokes `s_0`, `s_1`, ..., `s_8`),
or commands (`center`, `show`). The top element is marked using `[...]`.

In this case the user first made 9 strokes using the graphics tablet resulting in the state:
```
          s_0-s_7 [s_8]
```
These strokes represent the text "part 1" surrounded by a rectangle. Next, the user entered the `center` command:
```
          s_0-s_8 [center]
```
resulting in new strokes `s_9-s_17` that are centered on the screen. These strokes are part of the state:
```
          s_9-s_17
```
Finally the user enters the "show" command:
```
          s_9-s_17 [show]
```
this clears the stack and produces an animation:
```
|  @
```
Note that when entering commands from the keyboard the focus needs to be on the large window.

The large window always shows the strokes for the stack marked by the cursor. In the illustration above the cursor
is at:
```
|         s_9-s_17
```
and can be moved by holding down the CTRL key and pressing "j" or "k".

Pressing CTRL and "s" at the same time saves the resulting animations to `temp.mp4` and the resulting audio 
(in this case there is no audio) to "temp.wav".
To exit the program, focus on the large window and press ESCAPE.

More tutorial coming soon!
