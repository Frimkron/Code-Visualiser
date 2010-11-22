import ast
#import ubigraph
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
	children = []
	
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
	
class BranchPart(Construct):
	pass
	
		
class PythonConverter(ast.NodeVisitor):
	"""	
	Code file converter implementation for the Python programming language.
	"""
	
	def _remove_file_extension(self,filename):
		return ".".join(filename.split(".")[:-1])

	def convert_file(self, filepath):
		"""	
		Reads the given code file and outputs its contents as a syntax tree
		consisting of nested Construct objects.
		"""
		with open(filepath) as f:
			source = f.read()
		filename = os.path.basename(filepath)
		return self._convert_source(source, filename)

	def get_code_extensions(self):
		"""	
		Returns a sequence containing the possible source file extensions for
		this programming language
		"""
		return ("py",)

	def _convert_source(self, source, name):
		"""	
		Parses the given source string and returns its contents as a syntax
		tree consisting of nested Construct objects. Name is the name
		associated with the source (e.g. the filename)
		"""
		self.filename = name
		tree = ast.parse(source)
		return self.visit(tree)

	def visit_Module(self, node):
		"""	
		NodeVisitor hook - creates Package and descends into all children
		"""
		p = Package()
		p.name = self._remove_file_extension(self.filename)
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
			bp = BranchPart()
			bp.children = self._handle_fields(node,(field,))
			b.children.append(bp)
		return b					
					
	def _handle_fields(self, node, fields):
		"""	
		Calls 'visit' for each child node of the given node, in fields as 
		named by the 'fields' parameter, collecting the constructs fed 
		back and returning them as a flattened list.
		"""
		ret = []
		for field in fields:
			value = getattr(node,field)			
			# list of items
			if isinstance(value, list):
				for item in value:
					self._visit_and_collect(item,ret)
			# single item
			else:
				self._visit_and_collect(value,ret)
		if len(ret) > 0:
			return ret
			
	def _visit_and_collect(self, value, retlist):
		"""	
		Visits the item, if a node, flattens the result and adds to list
		"""
		if isinstance(value, ast.AST):
			r = self.visit(value)
			if r!=None:
				# visit may return a list if generic_visit was used
				if isinstance(r,list):
					retlist.extend(r)
				else:
					retlist.append(r)		
		
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
			self.handler.handle_create_dir(self._rel_path(event.path),event.name)
		else:
			self.handler.handle_create_file(self._rel_path(event.path),event.name)		
		
	def process_IN_DELETE(self, event):
		"""	
		pyinotify hook
		"""
		logging.info("%s deleted" % event.pathname)
		if event.dir:
			self.handler.handle_remove_dir(self._rel_path(event.path),event.name)
		else:
			self.handler.handle_remove_file(self._rel_path(event.path),event.name)
		
	def process_IN_MODIFY(self, event):
		"""	
		pyinotify hook
		"""
		logging.info("%s modified" % event.pathname)
		if not event.dir:
			self.handler.handle_change_file(self._rel_path(event.path),event.name)		
		
	def process_IN_MOVED_FROM(self, event):
		"""	
		pyinotify hook
		"""
		logging.info("%s moved out" % event.pathname)
		if event.dir:
			self.handler.handle_remove_dir(self._rel_path(event.path),event.name)
		else:
			self.handler.handle_remove_file(self._rel_path(event.path),event.name)
		
	def process_IN_MOVED_TO(self, event):
		"""	
		pyinotify hook
		"""
		logging.info("%s moved in" % event.pathname)
		if event.dir:
			self.handler.handle_create_dir(self._rel_path(event.path),event.name)
		else:
			self.handler.handle_create_file(self._rel_path(event.path),event.name)
		
	def _rel_path(self, path):
		return path[len(self.rootdir)+1:]
		
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
		Paths are relative to the given root directory
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

class FileUpdateException(Exception):
	pass

class ProjectManager(object):
	"""	
	Central class for tracking a code project. 
	"""

	def __init__(self, filemon, parser, output, dirpath, projname):
		"""	
		Takes a file monitor object, code parser object, output rendering object,
		path to project directory and the project name
		File monitor:
			run(dirpath,listener)
		Code parser:
			convert_file(filename)
			get_code_extensions()
		Output renderer:
			render(tree)
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
		# update output
		self.output.render(self.project)
		# begin monitoring changes
		self.filemon.run(self.dirpath, self)

	def _make_package_from_dir(self,dirpath,name):
		"""	
		Parses any code files in directory and recurses for nested directories. 
		Should be invoked to initialise the project. Returns a single package object 
		representing the directory. Name is the name to give the returned package.
		Package contents are added in name order.
		"""
		pkg = Package(name=name)
		children = []
		# iterate over directory contents
		for fname in sorted(os.listdir(dirpath)):
			fullpath = os.path.join(dirpath,fname)
			if os.path.isdir(fullpath):
				# item is a directory - recurse to add package as child
				children.append(self._make_package_from_dir(fullpath,fname))
			else:
				# item is a file. Is it a code file?
				if any(map(lambda ext: fname.endswith(ext), self.parser.get_code_extensions())):
					# parse file adding contents as child
					children.append(self.parser.convert_file(fullpath))
					
		pkg.children = children
		return pkg					

	def _create_package(self, path, name):
		"""	
		Creates a new package with the given name in the package
		identified by the project-relative file path, then invokes
		the output renderer to update.
		"""
		package = self._get_package(path)		
		
		package.children.append(Package(name=name))
		package.children.sort(key="name")

		# update output
		self.output.render(self.project)

	def _remove_node(self, path, name):
		"""	
		Removes a tree node represented by a file or directory,
		then invokes the output renderer to update.
		Path is the project-relative path of the directory the 
		file/directory resides in. Name is the name of the 
		file/directory.
		"""
		
		package = self._get_package(path)
		
		# find construct by name
		for i,child in enumerate(package.children):
			if child.name == name:
				# snip
				del(package.children[i])
				break
		else:
			# not found
			raise FileUpdateException("Node %s in %s does not exist" % (name,path))
		
		# update output
		self.output.render(self.project)

	def _update_file_contents(self, path, filename):
		"""	
		Creates or replaces the necessary nodes represented by the file
		identified by the given project-relative file path and file name.
		Then invokes output render to update.
		"""
		package = self._get_package(path)
		
		# TODO: filename to construct name!
		
		# find construct by name (may not exist)
		for i,child in enumerate(package.children):
			if child.name == name:
				# found existing, remove it
				del(package.children[i])
				break
				
		# parse file and add construct
		package.children.append(self.parser.convert_file(os.path.join(self.dirpath,path,filename)))
		package.children.sort(key="name")
		
		# update output
		self.output.render(self.project)

	def _get_package(self, path):
		"""	
		Returns the package identified by the project-relative file path.
		Raises FileUpdateException if this package does not exist
		"""
		# split path into package names
		pparts = []
		while not path in ("","/"):
			path,part = os.path.split(path)
			pparts.insert(0,part)

		# descend to correct package
		curr = self.project
		for pname in pparts:
			for child in curr.children:
				if child.name == pname:
					curr = child
					break
			else:
				# not found
				raise FileUpdateException("Package %s does not exist" % path)
		
		# return it
		return curr

	def handle_create_dir(self,path,name):
		"""	
		File monitor hook - invoked when a directory is created
		"""
		logging.info("dir %s created in %s" % (name,path))
		self._create_package(path,name)
		
	def handle_create_file(self,path,name):
		"""	
		File monitor hook - invoked when a file is created
		"""
		logging.info("file %s created in %s" % (name,path))
		self._update_file_contents(path,name)
		
	def handle_change_file(self,path,name):
		"""	
		File monitor hook - invoked when an existing file is altered
		"""
		logging.info("file %s changed in %s" % (name,path))
		self._update_file_contents(path,name)
		
	def handle_remove_dir(self,path,name):
		"""	
		File monitor hook - invoked when an existing directory is removed
		"""
		logging.info("dir %s removed from %s" % (name,path))
		self._remove_node(path,name)
		
	def handle_remove_file(self,path,name):
		"""	
		File monitor hook - invoked when an existing file is removed
		"""
		logging.info("file %s removed from %s" % (name,path))
		self._remove_node(path,name)


if __name__ == "__main__":
	if True:
		pass
	else:
		pass
	logging.basicConfig(level=logging.ERROR)
	f = FileMonitor()
	f.run(sys.argv[1], Test())
