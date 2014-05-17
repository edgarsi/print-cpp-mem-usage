# Copyright (C) 2014   ...
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import gdb, gdb.types
import sys, os, traceback, exceptions
from decorated_size import DecoratedSize


def sizeof_pointer():
	return gdb.lookup_type('void').pointer().sizeof

def sizeof_array(val, t, depth):
	length = t.sizeof / t.target().sizeof
	size = sizeof_variable(val[0], depth+1)
	if size.has_stl_objects:
		for i in range(1, length-1):
			size += sizeof_variable(val[i], depth+1)
	else:
		# We're in luck - the size of all elements is equal
		size *= length
	return size

# Cheat-sheet: https://github.com/blackjack/libstdcxx/blob/python3/v6/printers.py
# TODO: Detect small string optimizations because typical rep_size==24 where practically empty string is just 8
def sizeof_string(val, t, depth):
	indent = ' ' * depth * 4
	try:
		ptr = val['_M_dataplus']['_M_p']
		print indent + '_M_p: ' + str(ptr)
		realtype = t.unqualified().strip_typedefs()
		reptype = gdb.lookup_type(str(realtype) + '::_Rep').pointer()
		rep = (ptr.cast(reptype) - 1).dereference()
		print indent +'rep capacity ' + str(rep['_M_capacity']) + ' and refcount ' + str(rep['_M_refcount'])
		dynamic_size = long(rep['_M_capacity']) / long(rep['_M_refcount'] + 1) # GNU STL stores refcount as x-1 to make it initialized by default
		print indent + 'dynamic size ' + str(dynamic_size)
		rep_size = rep.type.sizeof / long(rep['_M_refcount'] + 1)
		print indent + 'rep size ' + str(rep_size)
		size = DecoratedSize.create_stl( t.sizeof + rep_size + dynamic_size )
	except:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print(indent, exc_type, fname, exc_tb.tb_lineno)
		raise
	print indent + "string size is " + str(size)
	return size

# Cheat-sheet: http://www.yolinux.com/TUTORIALS/src/dbinit_stl_views-1.03.txt
def sizeof_vector(val, t, depth):
	indent = ' ' * depth * 4
	try:
		size = DecoratedSize.create_stl( t.sizeof ) # std::vector overhead
		length = long(val['_M_impl']['_M_finish'] - val['_M_impl']['_M_start'])
		print indent + "length: " + str(length)
		#size += DecoratedSize.create_stl( length*sizeof_pointer() ) # std::vector stores pointers to elements. BS!
		print indent + "type of internal element: " + str(val['_M_impl']['_M_start'].type)
		if length > 0:
			pchildren = val['_M_impl']['_M_start']
			size_child = sizeof_variable(pchildren.dereference(), depth+1)
			if size_child.has_stl_objects or length == 1:
				#TODO: Support for monte carlo and extrapolating from average, if user agrees
				size += size_child
				for i in range(1, length):
					size += sizeof_variable(pchildren[i], depth+1)
			else:
				print indent + "oh lucky days"
				# We're in luck - the size of all elements is equal
				size += size_child*length
		# Reserved, unused memory
		type_size = val['_M_impl']['_M_start'].type.target().sizeof
		reserved_unused = long(val['_M_impl']['_M_end_of_storage'] - val['_M_impl']['_M_finish'])
		size += DecoratedSize.create_stl( type_size * reserved_unused )
	except:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print(indent, exc_type, fname, exc_tb.tb_lineno)
		raise
	print indent + "vector size is " + str(size)
	return size
	
def sizeof_shared_ptr(val, t, depth):
	indent = ' ' * depth * 4
	try:
		size = DecoratedSize.create_stl( t.sizeof )
		px = val['px']
		if px != 0:
			pn = val['pn']
			print indent + "pn " + str(pn) + " type " + str(pn.type)
			if pn.type.code == gdb.TYPE_CODE_PTR:
				# Compiled to use detail::atomic_count
				refcount = long(pn.dereference()['value_'])
				size += DecoratedSize.create_stl( pn.dereference().type.sizeof ) / refcount
			else:
				# Compiled to use detail::shared_count
				# Note that I don't cast to dynamic_type because practical usefulness is none and GCC cries over not having RTTI for
				# the sp_counted_impl_p<>. I even have to do ugly casting magic to avoid those warnings at dereference()
				pi_ = pn['pi_']
				print indent + 'pi_ ' + str(pi_) + ' type ' + str(pi_.type) + ' type->sizeof ' + str(pi_.type.target().sizeof) + (
					'') #' dynamic_type ' + str(pi_.dynamic_type) + ' dynamic_type->sizeof ' + str(pi_.dynamic_type.target().sizeof))
				#pi_.cast(gdb.lookup_type('int'))
				#refcount = long(pi_.dereference()['use_count_'])
				#realtype = pi_.type.target().unqualified().strip_typedefs()
				#print indent + 'realtype ' + str(realtype)
				#pi_base_type = gdb.lookup_type(str(realtype))
				#pi_as_void = pi_.cast(gdb.lookup_type('void').pointer())
				#print indent + 'as void'
				#refcount = long(pi_as_void.cast(pi_base_type.pointer()).dereference()['use_count_'])
				#print indent + 'woof'
				
				#offset = pi_.type.target()['use_count_'].bitpos / 8
				c = pi_.cast(gdb.lookup_type('char').pointer())
				#refcount = long(c[offset].cast(pi_.type.target()['use_count_'].type))
				refcount = long(c.dereference().cast(pi_.type.target())['use_count_'])
				
				size += DecoratedSize.create_stl( pi_.type.target().sizeof ) / refcount
				#size += DecoratedSize.create_stl( pi_.dynamic_type.target().sizeof ) / refcount
			print indent + "refcount: " + str(refcount)
			print indent + "dynamic_type: " + str(px.dynamic_type)
			px_real_type = px.cast(px.dynamic_type)
			print indent + "px: " +str(px) + " of type " + str(px.type)
			print indent + "px_real_type: " + str(px_real_type) + " of type " + str(px_real_type.type)
			size += sizeof_variable(px_real_type.dereference(), depth+1) / refcount #TODO: Don't traverse the same variable multiple times

	except:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print(indent, exc_type, fname, exc_tb.tb_lineno)
		raise
	return size

def sizeof_optional(val, t, depth):
	indent = ' ' * depth * 4
	try:
		if val['m_initialized']:
			size = DecoratedSize.create_stl( val['m_initialized'].type.sizeof ) # This is a big lie because ignores alignments.
			print indent + 'value_type ' + str(t.template_argument(0))
			stored_val = val['m_storage'].cast( t.template_argument(0) )
			print indent + 'stored_val ' + str(stored_val) + ' type ' + str(stored_val.type)
			size += sizeof_variable(stored_val)
		else:
			size = DecoratedSize.create_stl( t.sizeof )
	except:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print(indent, exc_type, fname, exc_tb.tb_lineno)
		raise
	return size


def sizeof_struct(val, t, depth):
	indent = ' ' * depth * 4
	for field in t.fields():
		print indent + str(field.name) + " type.sizeof:" + str(field.type.sizeof)
	
	# Count the size from the children
	size = DecoratedSize()
	#print help(gdb.Value)
	#print dir(gdb.Value)
	testing_t_keys = False
	testing_t_fields = True
	if testing_t_keys:
		for field in t.keys():
			try:
				#TODO: Fix template class field (incl base class) traversal
				print indent + "trying field " + field
				size += sizeof_variable(val[field], depth+1)
			except:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
				print(indent, exc_type, fname, exc_tb.tb_lineno)
	if testing_t_fields:
		# gdb.Type.fields() list does include instances of unnamed structs (I call them anonymous fields), yet it does
		# not include unnamed bitfields. GCC does not approve of unnamed int instances, and fair enough, not required by C++.
		for field in t.fields(): # Note that unnamed bitfields don't appear in this list although unnamed struct instances do
			try:
				#TODO: Fix template class field (incl base class) traversal
				print indent + "trying field " + field.name
				if not hasattr(field, 'bitpos'):
					print indent + "this is a static field"
				elif field.is_base_class:
					print indent + "this is a base class"
					#TODO: Base class sizeof is of a variable of that base class, so there's alignment which
					# may not occur then the base class is inherited. I should probably just use sizeof at
					# depth==0 and only traverse for STL instances.
					size += sizeof_variable(val.cast(field.type), depth+1)
				elif field.name == None or field.name == "":
					print indent + "this is an anonymous field"
					if field.bitpos % 8 == 0:
						# Ugly magic casting needed here
						offset = long(field.bitpos) / 8
						c = val.cast(gdb.lookup_type('char').array(offset))
						size += sizeof_variable(c[offset].cast(field.type), depth+1)
					else:
						# We can do nothing
						print indent + "at a messed up offset"
						size += DecoratedSize.create_anonymous(0)
				elif field.bitsize != 0 and field.type.sizeof != field.bitsize:
					# This is probably a bitfield. Handle as alignment because DecoratedSize has byte precision.
					print indent + "this is a bitfield"
				else:
					size += sizeof_variable(val[field.name], depth+1)
			except:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
				print(indent, exc_type, fname, exc_tb.tb_lineno)
				size += DecoratedSize.create_anonymous(0)
	
	# gdb.Value can find fields by name. At least tell the user that there are such fields even though
	# we can't traverse them. TODO: patch gdb
	#visible_children_size = 0
	#for field in t.keys():
	#	try:
	#		visible_children_size += val[field].type.sizeof
	#	except:
	#		# This is not a value field (probably)
	#		pass
	visible_children_size = size.size
	if visible_children_size < t.sizeof:
		# This is usually alignment or nonempty class restriction. In fact, this is so normal that I feel it's best to silently ignore any
		# mysterious sizes below pointer size. And even more, I traverse fields by t.fields which does list existance of anonymous
		# children even if it can't traverse them.
		# anonymous childrent are traversed.
		#print indent + "anonymous children! (" + str(t.sizeof - visible_children_size) + ")" # ...or imperfect alignment, no info on that <- yes info
		#size += DecoratedSize.create_anonymous( t.sizeof - visible_children_size )
		print indent + "alignment! (" + str(t.sizeof - visible_children_size) + ")"
		size += DecoratedSize.create_non_stl( t.sizeof - visible_children_size )
	
	return size


# TODO: Document that depth is recursion depth for debug, no the depth given as an argument. Done.
# TODO: Recursion state struct with long depth, long stl_depth, bool add_sizeof

# https://sourceware.org/gdb/current/onlinedocs/gdb/Types-In-Python.html#Types-In-Python
# TODO: non-byte 'char' detection for gdb.Type.sizeof calls?
def sizeof_variable(val, depth = 0):
	indent = ' ' * depth * 4
	try:
		print indent + "counting " + str(val) + " of type " + str(val.type) + " and type.sizeof " + str(val.type.sizeof)
		#size = DecoratedSize()
		#t = val.type.strip_typedefs() #TODO: Use gdb.Value.dynamic_type <- what's the use if we don't dereference pointers? smart_ptr!
		#t = val.dynamic_type
		t = val.type.strip_typedefs()
		str_t = str(t)
		#if val.type != t:
		#	print indent + "dynamic type " + str_t

		if t.code == gdb.TYPE_CODE_ARRAY:
			size = sizeof_array(val, t, depth)
			
		elif t.code == gdb.TYPE_CODE_STRUCT:
			if str_t.startswith('std::basic_string<'):
				size = sizeof_string(val, t, depth)
			elif str_t.startswith('std::vector<'):
				size = sizeof_vector(val, t, depth)
			elif str_t.startswith('boost::shared_ptr<'):
				size = sizeof_shared_ptr(val, t, depth)
			elif str_t.startswith('boost::optional<'):
				size = sizeof_optional(val, t, depth)
			else:
				size = sizeof_struct(val, t, depth)
			
		elif t.code == gdb.TYPE_CODE_PTR:
			if str_t == 'int (**)(void)': # chances are high this is _vptr. TODO: better detection
				size = DecoratedSize.create_non_stl( t.sizeof )
			else:
				if val == 0:
					size = DecoratedSize.create_null_pointer( t.sizeof )
				else:
					size = DecoratedSize.create_nonnull_pointer( t.sizeof )
			
		else: # t.code is a trivial type
			print indent + "trivial type"
			size = DecoratedSize.create_non_stl( t.sizeof )
		
		if t.code == gdb.TYPE_CODE_UNION:
			print indent + "union!!! " + str(t.sizeof)
			# Either perspective may reveal interesting substructures such as pointers but
			# we only need the real size of one. I do not care if an STL structure is counted
			# twice because putting them in a union is horrible. I will assume the least
			# awful version where each perspective has different STL objects and somehow pads
			# over those of others.
			size_as_struct = sizeof_struct(val, t, depth)
			print "size_as_struct " + str(size_as_struct) + " removing " + str(long(t.sizeof))
			size = size_as_struct - DecoratedSize.create_non_stl(long(t.sizeof))
			if size.has_stl_objects:
				print indent + "madman puts STL objects in a union!"
				size += DecoratedSize.create_anonymous(0) #TODO: create_unknown makes more sense
		
		elif t.code == gdb.TYPE_CODE_FLAGS:
			print "flags!!! " +str(t.sizeof)
		elif t.code == gdb.TYPE_CODE_FUNC:
			print "function!!! " + str(t.sizeof)
		elif t.code == gdb.TYPE_CODE_VOID:
			print "void!!! " + str(t.sizeof)
		elif t.code == gdb.TYPE_CODE_REF:
			print "ref!!! " + str(t.sizeof) # size is 8 which is great
		elif t.code == gdb.TYPE_CODE_TYPEDEF:
			print "typedef!!! " + str(t.sizeof)
		
	except:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print(indent, exc_type, fname, exc_tb.tb_lineno)
		raise
	#print repr(traceback.format_stack())
	print indent + "returning " + str(size)
	return size
	
#visited_types = set()
def print_block(block, frame = None):
	#global visited_types
	print str(block) + ' in function ' + str(block.function)
	for symbol in block:
		#print symbol.name
		if symbol.is_variable and ( True
		and symbol.print_name not in ['fp', 'vd', 'vde', 'evilvar', 'e', 'es', 'vs', 'di', 'bc', 'bf', 'd2', 'a', 'sb', 'dummy' ]
		and symbol.print_name not in ['s0', 's0x10', 's1', 's2', 's3', 's4', 's10', 's10r', 'd', 'r', 'p', 'dx10', 'std::__ioinit', 's10x10', 'u', 'o', 'oc', 'od' ]
		and symbol.print_name not in ['hmm', 'i', 'j', 'var_in_main', 'var_in_main_2', 'static_in_main', 'ms' ]
		):
			print symbol.print_name
			print symbol.type
			if frame == None:
				print sizeof_variable(symbol.value())
			else:
				print sizeof_variable(frame.read_var(symbol, block))
			print
		#elif symbol.type != None and symbol.type.tag == gdb.TYPE_CODE_STRUCT:
		#	if symbol.type.name not in visited_types:
		#		print str(symbol.type)
		#		visited_types.add(symbol.type.name)
			#try:
			#	type = gdb.lookup_type(symbol.name, block)
			#	#type = gdb.lookup_type(symbol.name)
			#	print str(type)
			#except gdb.error:
			#	pass
	

class PrintCppMemUsage(gdb.Command):
	'Print C++ memory usage statistics'
	def __init__(self):
		gdb.Command.__init__(self, "print-cpp-mem-usage", gdb.COMMAND_DATA)
	
	def invoke(self, args, from_tty):
		print 'hello!'
		print gdb.Symtab.filename
		print gdb.Symtab.objfile
		try:
			symtab = gdb.selected_frame().find_sal().symtab
		except gdb.error:
			raise gdb.GdbError("No frame selected")
		try:
			print symtab.is_valid()
		except exceptions.AttributeError:
			raise gdb.GdbError("No symbol information in your program")
		print symtab.fullname()
		#print_block(symtab.global_block())
		#print_block(symtab.static_block())
		
		#for objfile in gdb.objfiles():
		#	print objfile.filename
		
		# The best we can do is iterate the stack and global&static variables of the files of the functions in the stack.
		# It is bound to be a source of frustration but I prefer doing the best I can do to skipping global&static altogether.
		# Other people support the nonexistance of any way to do better, and GDB changelog gives no presents either.
		# http://stackoverflow.com/questions/16585683/core-dump-extract-all-the-global-variables-data-structures-and-sub-structure
		# TODO: This is not completely true... I can list all variables using CLI and issue gdb.block_for_pc on each address.
		frame = gdb.selected_frame()
		#frame = gdb.newest_frame()
		symtabs_seen = set()
		while frame != None:
			print 'Frame ' + str(frame.name()) + ' read from frame.block()'
			block = frame.block()
			while block != None and not block.is_global and not block.is_static:
				print_block(block, frame)
				block = block.superblock
			symtab = frame.find_sal().symtab
			print 'Symtab fullname is ' + symtab.fullname()
			if symtab.fullname() not in symtabs_seen:
				print_block(symtab.global_block())
				print_block(symtab.static_block())
				symtabs_seen.add(symtab.fullname())
			
			#print 'Frame ' + str(frame.name()) + ' read from pc'
			##block = gdb.block_for_pc(frame.pc())
			#block = gdb.block_for_pc(frame.find_sal().pc)
			#while block != None:
			#	print_block(block, frame)
			#	block = block.superblock
			frame = frame.older()
		#TODO: each_block_exec(print_block)
		#TODO: Macros because I need to design for speed here


PrintCppMemUsage()

