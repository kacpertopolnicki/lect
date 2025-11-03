- when there are no recordings or animations and CTRL-a is pressed
  the program raises an error and terminates - this should be
  handled
- fix opacity issues across `PIL` and `pyglet`
  - seems to work ok in `pyglet`
  - `PIL` `draw` needs to be in `RGBA` mode
    to layer strokes with different colors
    and alpha
  - conversion to `BGR` might need to be manual
- add tests
- strengthen immutability of State
   - verify that they don't change (images are not copied, 
     can you make a numpy array immutable?)
   - _additional is large and is not copied, is this important?
- pickle some records and use this for tests
- make the code after ctrl-s ctrl-a parallel
- add documentation
- add tutorial to README.md
