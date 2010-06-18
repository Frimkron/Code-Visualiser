import ast

"""	
Structure:
	FunctionDef name, body
	ClassDef name, body
	Module body

Sequence:
	Call func args keywords starargs kwargs
	Import names
	
Branching:
	If test, body, orelse
	TryExcept body handlers orelse
	ExceptHandler type name body
	With context_expr optional_vars body

Iteration:
	For target iter body orelse
	While test body orelse
"""

class Construct(object):
	name = None
	children = ()

class Package(Construct):
	pass

class Class(Construct):
	pass

class Function(Construct):
	pass

class Iteration(Construct):
	pass

class Branch(Construct):
	pass
