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
3) `lect -h` should give some information on how to run the program

# todo

Below is a partial list of things that need to be done:

- add tests
- strengthen immutability of State
   - verify that they don't change (images are not copied, 
     can you make a numpy array immutable?)
   - _additional is large and is not copied, is this important?
- pickle some records and use this for tests
- make the code after ctrl-s ctrl-a parallel
- add documentation
- setup code structure for pip
- add tutorial to README.md
- remove most calls to logger.debug
- read todos in code :-) 
