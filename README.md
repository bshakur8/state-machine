# State-Machine

Python 3.6 library that simulates a state machine.

A state machine is consisted from states, start state, and transitions table.  
State: Gets input, and runs a given function on it. The results is being returned to an inner objects called 
Coordinator that calculated the next state based on the current state and result.

Each State has number of process workers.