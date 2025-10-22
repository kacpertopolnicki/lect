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
5) Deactivate environent after you are done working with lect.

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
5) Naviate to the directory with the `lect` script.
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
programm. Each line represents a single state. For example:

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
- `0` marks the beginning of the programm,
- `|` marks the current position of the cursor.
In the next column:
- `@` marks that there is some audio and video date associated with a state.
The following columns contain the stack for each state. The stack can be empty,
can contain strokes created by the user using a graphics tablet (`s_0-s_8` measns strokes `s_0`, `s_1`, ..., `s_8`),
or commands (`center`, `show`).

There is another window associated with graphics tablet input. The setup may look like this:

![](https://github.com/kacpertopolnicki/lect/blob/main/readme_resources/sc.png)

Where the small window is the terminal and the larger window is for drawing with a graphics tablet.

