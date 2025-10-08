# lect

A simple recorder for lectures and presentations.
Currently in early stages of development. 

Traditionally, information in technical subjects (mathematics, physics, ...)
was shared using chalk and a blackboard. This simple medium is surprisingly
efficient and *lect* is a modern take on this approach. 

# usage

Use at your own risk!

In order to run the program:

1) A graphics tablet must be connected to the computer 
   (there will be an error if no graphics tablet is detected).
2) `lect` needs to be ran in an environment with:
   - `curses`, `numpy`, `pyglet`, `PIL`, `cv2`, `sounddevice`, `pyperclip`
   - `lect -h` should give some information on how to run the program

# todo

Below is a partial list of things that need to be done:

1) add tests
2) strengthen immutability of State
   - verify that they don't change (images are not copied, 
     can you make a numpy array immutable?)
   - _additional is large and is not copied, is this important?
3) pickle some records and use this for tests
4) make the code after ctrl-s ctrl-a parallel
5) add documentation
6) setup code structure for pip
7) add tutorial to README.md
10) remove most calls to logger.debug
11) read todos in code :-) 
