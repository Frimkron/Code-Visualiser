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
	
	def __init__(self,name=None,children=None):
		self.name = name
		self.children = children
	
	def __repr__(self):
		return "%s(%s,%s)" % (self.__class__.__name__,repr(self.name),repr(self.children))

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


class CodeFileConverter(object):
	
	def convert_file(self, filename): 
		self.filename = filename
		with open(filename) as f:
			source = f.read()
		return self.convert_source(source)
		
	def convert_source(self, source): 
		pass
		
	def remove_file_extension(self, filename):
		return ".".join(filename.split(".")[:-1])
		
class PythonConverter(CodeFileConverter, ast.NodeVisitor):

	def convert_source(self, source):
		tree = ast.parse(source)
		return self.visit(tree)

	def visit_Module(self, node):
		p = Package()
		p.name = self.remove_file_extension(self.filename)
		p.children = self.generic_visit(node)
		return p

	def visit_ClassDef(self, node):
		c = Class()
		c.name = node.name
		c.children = self.handle_fields(node,("body",))
		return c
		
	def visit_FunctionDef(self, node):
		f = Function()
		f.name = node.name
		f.children = self.handle_fields(node,("body",))
		return f
		
	def visit_If(self, node):
		return self.make_branch(node,("body","orelse"))
		
	def visit_TryExcept(self, node):
		# TODO: handlers
		return self.make_branch(node,("body","orelse"))
		
	def visit_TryFinally(self,node):
		return self.make_branch(node,("body","finalbody"))
		
	def visit_While(self, node):
		# TODO: else
		i = Iteration()
		i.children = self.handle_fields(node,("body",))
		return i
		
	def visit_For(self, node):
		# TODO: else
		i = Iteration()
		i.children = self.handle_fields(node,("body",))
		return i
		
	def make_branch(self, node, branch_fields):
		b = Branch()
		b.children = []
		for field in branch_fields:
			value = getattr(node,field)
			r = self.handle_fields(node,(field,))
			if r!=None: b.children.append(r)
		return b					
					
	def handle_fields(self, node, fields):
		ret = []
		for field in fields:
			value = getattr(node,field)			
			if isinstance(value, list):
				for item in value:
					if isinstance(item, ast.AST):
						r = self.visit(item)					
						if r!=None: ret.append(r)
			elif isinstance(value, ast.AST):
				r = self.visit(value)
				if r!=None: ret.append(r)
		if len(ret) > 0:
			return ret
		
	def generic_visit(self,node):
		return self.handle_fields(node,node._fields)
	
