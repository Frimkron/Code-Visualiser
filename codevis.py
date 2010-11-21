import ast
import ubigraph
import sys
import os
import os.path
import time
import pyinotify
import logging

class Construct(object):
	"""	
	Base class for syntax tree nodes.
	"""
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
	"""	
	Base class for programming language parsers.
	"""
	
	def convert_file(self, filepath):
		"""	
		Reads the given code file and outputs its contents as a syntax tree
		consisting of nested Construct objects.
		"""
		with open(filepath) as f:
			source = f.read()
		filename = os.path.basename(filepath)
		return self.convert_source(source, filename)
		
	def convert_source(self, source, name): 
		"""	
		Parses the given source string and returns its contents as a syntax
		tree consisting of nested Construct objects. Name is the name
		associated with the source (e.g. the filename)
		"""
		pass
		
	def remove_file_extension(self, filename):
		"""	
		Helper for removing the file extension from the given filename
		"""
		return ".".join(filename.split(".")[:-1])
		
	def get_code_extensions(self):
		"""	
		Returns a sequence containing the possible source file extensions for
		this programming language
		"""
		pass
	
		
class PythonConverter(CodeFileConverter, ast.NodeVisitor):
	"""	
	CodeFileConverter implementation for the Python programming language.
	"""

	def get_code_extensions(self):
		"""	
		Overidden from CodeFileConverter. Returns possible Python code file
		extensions.
		"""
		return ("py",)

	def convert_source(self, source, name):
		"""	
		Overidden from CodeFileConverter. Parses the given source string and
		returns the Construct tree. Name is not used.
		"""
		tree = ast.parse(source)
		return self.visit(tree)

	def visit_Module(self, node):
		"""	
		NodeVisitor hook - creates Package and descends into all children
		"""
		p = Package()
		p.name = self.remove_file_extension(self.filename)
		p.children = self.generic_visit(node)
		return p

	def visit_ClassDef(self, node):
		"""	
		NodeVisitor hook - creates Class and descends into body
		"""
		c = Class()
		c.name = node.name
		c.children = self._handle_fields(node,("body",))
		return c
		
	def visit_FunctionDef(self, node):
		"""	
		NodeVisitor hook - creates Function and descends into body
		"""
		f = Function()
		f.name = node.name
		f.children = self._handle_fields(node,("body",))
		return f
		
	def visit_If(self, node):
		"""	
		NodeVisitor hook - creates Branch from body and orelse
		"""
		return self._make_branch(node,("body","orelse"))
		
	def visit_TryExcept(self, node):
		"""	
		NodeVisitor hook - creates Branch from body and orelse
		"""
		# TODO: handlers
		return self._make_branch(node,("body","orelse"))
		
	def visit_TryFinally(self,node):
		"""	
		NodeVisitor hook - creates Branch from body and finalbody
		"""
		return self._make_branch(node,("body","finalbody"))
		
	def visit_While(self, node):
		"""	
		NodeVisitor hook - creates Iteration and descends into body
		"""
		# TODO: else
		i = Iteration()
		i.children = self._handle_fields(node,("body",))
		return i
		
	def visit_For(self, node):
		"""	
		NodeVisitor hook - creates Iteration and descends into body
		"""
		# TODO: else
		i = Iteration()
		i.children = self._handle_fields(node,("body",))
		return i
		
	def _make_branch(self, node, branch_fields):
		"""	
		Constructs a Branch object from the given node, adding the children of 
		the nodes contained in the named fields as branch children.
		"""
		b = Branch()
		b.children = []
		for field in branch_fields:
			value = getattr(node,field)
			r = self._handle_fields(node,(field,))
			if r!=None: b.children.append(r)
		return b					
					
	def _handle_fields(self, node, fields):
		"""	
		Calls 'visit' for each child node of the given node, in fields as 
		named by the 'fields' parameter, collecting the return values fed 
		back and returning them as a list where not None.
		"""
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
		"""	
		Overidden from NodeVisitor. Invoked when no 'visit_X' handler method
		exists for 'visit' to call.
		"""
		return self._handle_fields(node,node._fields)
	
	
class FileMonitor(pyinotify.ProcessEvent):
	"""	
	File monitor implementation which uses pyinotify to listen for file
	system changes.
	"""

	def process_IN_CREATE(self, event):
		"""	
		pyinotify hook
		"""
		logging.info("%s created" % event.pathname)
		if event.dir:
			self.handler.handle_create_dir(event.path,event.name)
		else:
			self.handler.handle_create_file(event.path,event.name)		
		
	def process_IN_DELETE(self, event):
		"""	
		pyinotify hook
		"""
		logging.info("%s deleted" % event.pathname)
		if event.dir:
			self.handler.handle_remove_dir(event.path,event.name)
		else:
			self.handler.handle_remove_file(event.path,event.name)
		
	def process_IN_MODIFY(self, event):
		"""	
		pyinotify hook
		"""
		logging.info("%s modified" % event.pathname)
		if not event.dir:
			self.handler.handle_change_file(event.path,event.name)		
		
	def process_IN_MOVED_FROM(self, event):
		"""	
		pyinotify hook
		"""
		logging.info("%s moved out" % event.pathname)
		if event.dir:
			self.handler.handle_remove_dir(event.path,event.name)
		else:
			self.handler.handle_remove_file(event.path,event.name)
		
	def process_IN_MOVED_TO(self, event):
		"""	
		pyinotify hook
		"""
		logging.info("%s moved in" % event.pathname)
		if event.dir:
			self.handler.handle_create_dir(event.path,event.name)
		else:
			self.handler.handle_create_file(event.path,event.name)
		
	def run(self, rootdir, handler):
		"""	
		Main loop - invoked to begin monitoring the file system.
		rootdir is the directory to monitor, handler is an object with the
		following methods:
			handle_create_dir(path,name)
			handle_create_file(path,name)
			handle_change_file(path,name)
			handle_remove_dir(path,name)
			handle_remove_file(path,name)
		"""
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
	"""	
	Central class for tracking a code project. 
	"""

	def __init__(self, filemon, parser, output, dirpath, projname):
		"""	
		Takes a file monitor object, code parser object, output rendering object,
		path to project directory and the project name
		"""
		self.filemon = filemon
		self.parser = parser
		self.output = output
		self.dirpath = dirpath
		self.project = None
		self.project_name = projname
		
		# initialise the project
		self.project = self._make_package_from_dir(self.dirpath,self.project_name)

	def manage(self):
		"""	
		Main loop - invoked to begin monitoring the project
		"""
		self.filemon.run(self.dirpath, self)

	def _make_package_from_dir(self,dirpath,name):
		"""	
		Parses any code files in directory and recurses for nested directories. 
		Should be invoked to initialise the project. Returns a single package object 
		representing the directory. Name is the name to give the returned package.
		"""
		pkg = Package(name=name)
		children = []
		# iterate over directory contents
		with fname in os.listdir(dirpath):
			fullpath = os.path.join(dirpath,fname)
			if os.path.isdir(fullpath):
				# item is a directory - recurse to add package as child
				children.append(self._make_package_from_dir(fullpath,fname)
			else:
				# item is a file. Is it a code file?
				if any(map(lambda ext: fname.endswith(ext), self.parser.get_code_extensions())):
					# parse file adding contents as child
					children.append(parser.convert_file(fullpath))
					
		pkg.children = tuple(children)
		return pkg					

	def _create_package(self, path, name):
		# TODO: check path exists, create package, invoke render
		pass

	def _remove_node(self, path, name):
		# TODO: check path exists, remove node and children, invoke render
		# this method can remove packages, classes or whatever might be 
		# represented by a file or directory, and has a name.
		pparts = []
		while not path in ("","/"):
			path,part = os.path.split(path)
			pparts.insert(0,part)
		
		pass

	def _update_file_contents(self, path, filename):
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
		"""	
		File monitor hook - invoked when a directory is created
		"""
		print "dir %s created in %s" % (name,path)
		# TODO: call create_package
		
	def handle_create_file(self,path,name):
		"""	
		File monitor hook - invoked when a file is created
		"""
		print "file %s created in %s" % (name,path)
		# TODO: call update_file_contents
		
	def handle_change_file(self,path,name):
		"""	
		File monitor hook - invoked when an existing file is altered
		"""
		print "file %s changed in %s" % (name,path)
		# TODO: call update_file_contents
		
	def handle_remove_dir(self,path,name):
		"""	
		File monitor hook - invoked when an existing directory is removed
		"""
		print "dir %s removed from %s" % (name,path)
		# TODO: call remove_node
		
	def handle_remove_file(self,path,name):
		"""	
		File monitor hook - invoked when an existing file is removed
		"""
		print "file %s removed from %s" % (name,path)
		# TODO call remove_node

logging.basicConfig(level=logging.ERROR)
f = FileMonitor()
f.run(sys.argv[1], Test())
