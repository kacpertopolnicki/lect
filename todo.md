- when there are no recordings or animations and CTRL-a is pressed
  the program raises an error and terminates - this should be
  handled
- there are strange errors in `PIL` when drawing strokes with `_simple_stroke_shapes`,
  this is not a problem in `pyglet`
  - the new function should work better with opacity
- fix opacity issues across `PIL` and `pyglet`
