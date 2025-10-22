- when there are no recordings or animations and CTRL-a is pressed
  the program raises an error and terminates - this should be
  handled
- there are strange errors in `PIL` when drawing strokes with `_simple_stroke_shapes`,
  this is not a problem in `pyglet`
  - the new function should work better with opacity
- fix opacity issues across `PIL` and `pyglet`
- add tests
- strengthen immutability of State
   - verify that they don't change (images are not copied, 
     can you make a numpy array immutable?)
   - _additional is large and is not copied, is this important?
- pickle some records and use this for tests
- make the code after ctrl-s ctrl-a parallel
- add documentation
- add tutorial to README.md
