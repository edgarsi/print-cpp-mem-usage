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

import copy

# http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
def bytes_format(num):
	for x in ['','K','M','G','T']:
		if (num < 1024.0 and num > -1024.0) or (x == 'T'):
			return ("%.1f%s" % (num, x)).rstrip('0').rstrip('.')
		num /= 1024.0

class DecoratedSize:
	'Size of a variable with details about composition, accuracy'

	@staticmethod
	def create_non_stl(size):
		new = DecoratedSize(size)
		return new
	@staticmethod
	def create_stl(size):
		new = DecoratedSize(size)
		new.has_stl_objects = True
		return new
	@staticmethod
	def create_anonymous(size):
		new = DecoratedSize(size)
		new.has_anonymous_objects = True
		return new
	@staticmethod
	def create_null_pointer(size):
		new = DecoratedSize(size)
		new.has_pointers = True
		return new
	@staticmethod
	def create_nonnull_pointer(size):
		new = DecoratedSize(size)
		new.has_pointers = True
		new.has_nonnull_pointers = True
		return new
	
	def __init__(self, size = 0):
		self.size = size
		#TODO: shared_ptr, weak_ptr support
		self.has_stl_objects = False
		self.has_anonymous_objects = False
		self.has_pointers = False
		self.has_nonnull_pointers = False
	
	def __add__(self, other):
		# TODO: Implement __radd__ and ban use of __add__ - avoid deep copies that way
		#print "Adding " + str(self) + " and " + str(other)
		total = copy.deepcopy(self)
		total.size += other.size
		total.has_stl_objects |= other.has_stl_objects
		total.has_anonymous_objects |= other.has_anonymous_objects
		total.has_pointers |= other.has_pointers
		total.has_nonnull_pointers |= other.has_nonnull_pointers
		#print "Adding results in " + str(total)
		return total
	
	def __sub__(self, other):
		tmp = copy.deepcopy(other)
		tmp.size = 0 - tmp.size
		return self + tmp
	
	def __mul__(self, num):
		print "__mul__"
		total = copy.deepcopy(self)
		total.size *= num
		# Treat all pointers are possibly nonnull. This is unlikely to be confusing often.
		# This is done because multiplication implies more elements of the same type, no info on their values.
		if total.has_pointers:
			total.has_nonnull_pointers = True
		return total
	#def __rmul__(num, self):
	#	print "__rmul__"
	#	return __mul__(self, num)
	#def __imul__(self, num):
	#	print "__imul__ " + str(self) + " * + " + str(num)
	#	self.size *= num
	#	return self
	
	def __div__(self, num):
		total = copy.deepcopy(self)
		total.size //= num
		return total
	
	def __str__(self):
		return (('~' if self.has_stl_objects else '') 
			+ bytes_format(self.size)
			+ (' + ? unknown' if self.has_anonymous_objects or self.has_nonnull_pointers else '')
		)

