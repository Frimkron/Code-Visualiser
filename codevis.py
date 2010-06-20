import ast
import ubigraph
import sys
import os
import time
import pyinotify
import logging

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
		
	def get_code_extensions(self):
		pass
		
class PythonConverter(CodeFileConverter, ast.NodeVisitor):

	def get_code_extensions(self):
		return ("py",)

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
	
class FileMonitor(pyinotify.ProcessEvent):

	def process_IN_CREATE(self, event):
		logging.info("%s created" % event.pathname)
		if event.dir:
			self.handler.handle_create_dir(event.path,event.name)
		else:
			self.handler.handle_create_file(event.path,event.name)		
		
	def process_IN_DELETE(self, event):
		logging.info("%s deleted" % event.pathname)
		if event.dir:
			self.handler.handle_remove_dir(event.path,event.name)
		else:
			self.handler.handle_remove_file(event.path,event.name)
		
	def process_IN_MODIFY(self, event):
		logging.info("%s modified" % event.pathname)
		if not event.dir:
			self.handler.handle_change_file(event.path,event.name)		
		
	def process_IN_MOVED_FROM(self, event):
		logging.info("%s moved out" % event.pathname)
		if event.dir:
			self.handler.handle_remove_dir(event.path,event.name)
		else:
			self.handler.handle_remove_file(event.path,event.name)
		
	def process_IN_MOVED_TO(self, event):
		logging.info("%s moved in" % event.pathname)
		if event.dir:
			self.handler.handle_create_dir(event.path,event.name)
		else:
			self.handler.handle_create_file(event.path,event.name)
		
	def run(self, rootdir, handler):
		self.rootdir = rootdir
		self.handler = handler
		self.wm = pyinotify.WatchManager()
		self.mask = ( pyinotify.IN_DELETE | pyinotify.IN_CREATE 
			| pyinotify.IN_MODIFY | pyinotify.IN_MOVED_FROM 
			| pyinotify.IN_MOVED_TO )
		self.notifier = pyinotify.Notifier(self.wm, self)
		self.wm.add_watch(self.rootdir,self.mask,rec=True,auto_add=True)
		self.notifier.loop()

class FileUpdateException(exception):
	pass

class ProjectManager(object):

	def __init__(self, filemon, parser, output, dirpath):
		self.filemon = filemon
		self.parser = parser
		self.output = output
		self.dirpath = dirpath
		self.project = None

	def manage(self):
		self.filemon.run(self.dirpath, self)

	def create_package(self, path, name):
		# TODO: check path exists, create package, invoke render
		pass

	def remove_node(self, path, name):
		# TODO: check path exists, remove node and children, invoke render
		# this method can remove packages, classes or whatever might be 
		# represented by a file or directory, and has a name.
		pass

	def update_file_contents(self, path, filename):
		# TODO: check path exists, parse file, replace structure, invoke render
		pass
	"""	
	def update_file(self, filepath, isdir):
		# split path
		p = []
		while not filepath in ("","/"):
			filepath, part = os.path.split(filepath)
			p.insert(0,part)		
		target = p[-1]
		p = p[:-1]
		
		# walk down packages to one containing target
		if self.project==None or self.project.name!=p[0]:
			raise FileUpdateException(p[0])
			
		curnode = self.project	
		for i in range(1,len(p)):
			packagename = p[i]
			found = False
			for child in curnode.children:
				if isinstance(child,Package) and child.name == packagename:
					curnode = child
					found = True
					break
			if not found:
				raise FileUpdateException(os.path.join(p[:i+1]))
	"""	

	def handle_create_dir(self,path,name):
		print "dir %s created in %s" % (name,path)
		
	def handle_create_file(self,path,name):
		print "file %s created in %s" % (name,path)
		
	def handle_change_file(self,path,name):
		print "file %s changed in %s" % (name,path)
		
	def handle_remove_dir(self,path,name):
		print "dir %s removed from %s" % (name,path)
		
	def handle_remove_file(self,path,name):
		print "file %s removed from %s" % (name,path)

logging.basicConfig(level=logging.ERROR)
f = FileMonitor()
f.run(sys.argv[1], Test())
