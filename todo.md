- add tests
   - alternatively just use the thing for a while
     and fix things when they seem broken?
   - once a thing gets broken and fixed add a test,
     this will prevent the same problem from happening
     in future
    - pickle some records and use this for tests
- change how opacity is handled in stackfunctions
  - now that opacity is fixed it can be used instead
    of fading into the background
- strengthen immutability of State
   - verify that they don't change (images are not copied, 
     can you make a numpy array immutable?)
   - _additional is large and is not copied, is this important?
- make the code after ctrl-s ctrl-a parallel
- add documentation
- add tutorial to README.md
