# Based on https://github.com/arvidn/struct_layout:
#
# Copyright (c) 2013, Arvid Norberg
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#       the documentation and/or other materials provided with the distribution.
#     * Neither the name of the author nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from collections import namedtuple
import parsy
import re

class DwarfBase:

	def has_fields(self):
		return False

	def size(self):
		return 0

	def match(self, f):
		return False

	def print_struct(self):
		pass

	def full_name(self):
		return ''

class DwarfTypedef(DwarfBase):

	def __init__(self, item, scope, types):
		self._scope = scope
		self._types = types
		if 'AT_type' in item['fields']:
			self._underlying_type = item['fields']['AT_type']
		else:
			# this means "void"
			self._underlying_type = 0

	def size(self):
		return self._types[self._underlying_type].size()

	def name(self):
		if self._underlying_type == 0:
			return 'void'
		else:
			return self._types[self._underlying_type].name()

	def full_name(self):
		if self._underlying_type == 0:
			return 'void'
		else:
			return self._types[self._underlying_type].full_name()

	def has_fields(self):
		if self._underlying_type == 0: return False
		return self._types[self._underlying_type].has_fields()

	def print_fields(self, offset, expected, indent, prof, cache_lines):
		if self._underlying_type == 0: return 0
		return self._types[self._underlying_type].print_fields(offset, expected, indent, prof, cache_lines)

	def match(self, f):
		if self._underlying_type == 0: return False
		return self._types[self._underlying_type].match(f)

	def print_struct(self):
		if self._underlying_type == 0: return
		self._types[self._underlying_type].print_struct()

class DwarfVoidType(DwarfBase):

	def __init__(self, item, scope, types):
		pass

	def name(self):
		return 'void'

class DwarfConstType(DwarfTypedef):

	def name(self):
		return 'const ' + DwarfTypedef.name(self)

class DwarfVolatileType(DwarfTypedef):

	def name(self):
		return 'volatile ' + DwarfTypedef.name(self)

class DwarfPointerType(DwarfTypedef):

	def size(self):
		global pointer_size
		return pointer_size

	def name(self):
		return DwarfTypedef.name(self) + '*'

	def has_fields(self):
		return False

class DwarfFunPtrType(DwarfBase):

# TODO: support function signatures (for function pointers)

	def __init__(self, item, scope, types):
		self._scope = scope
		pass

	def size(self):
		return 0

	def name(self):
		return '<fun_ptr>'

	def match(self, f): return False

	def has_fields(self):
		return False

class DwarfReferenceType(DwarfTypedef):

	def size(self):
		global pointer_size
		return pointer_size

	def name(self):
		return DwarfTypedef.name(self) + '&'

	def has_fields(self):
		return False

class DwarfRVReferenceType(DwarfReferenceType):

	def name(self):
		return DwarfTypedef.name(self) + '&&'

class DwarfArrayType(DwarfBase):

	def __init__(self, item, scope, types):
		self._scope = scope
		if 'AT_upper_bound' in item['children'][0]['fields']:
			self._num_elements = int(item['children'][0]['fields']['AT_upper_bound'], 16) + 1
		else:
			# this means indeterminate number of items
			# (i.e. basically a regular pointer)
			self._num_elements = -1

		self._underlying_type = item['fields']['AT_type']
		self._types = types

	def size(self):
		return self._types[self._underlying_type].size() * self._num_elements

	def name(self):
		return self._types[self._underlying_type].name() + '[%d]' % self._num_elements

class DwarfBaseType(DwarfBase):

	def __init__(self, item, scope, types):
		self._scope = scope
		if 'AT_name' in item['fields']:
			self._name = item['fields']['AT_name']
		else:
			self._name = '(anonymous)'

		self._size = int(item['fields']['AT_byte_size'], 16)

	def size(self):
		return self._size

	def name(self):
		return self._name

class DwarfEnumType(DwarfBaseType):

	def name(self):
		return 'enum ' + self._name

class DwarfMember:
	def __init__(self, item, types):
		self._types = types
		self._underlying_type = item['fields']['AT_type']
		self._offset = int(item['fields']['AT_data_member_location'])
		if 'AT_name' in item['fields']:
			self._name = item['fields']['AT_name']
		else:
			self._name = '<base-class>'

	def print_field(self, offset, expected, indent, prof, cache_lines):
		t = self._types[self._underlying_type]
		num_padding = (self._offset + offset) - expected
		global color_output
		global prof_max
		global barcolor
		global restore
		global padcolor
		global cachecol

		if prof != None:
			# access profile mode
			if t.has_fields():

				if self._name == '<base-class>': name = '<base-class> %s' % t.name()
				else: name = self._name
				name_field = '%s%s' % ((' ' * indent), name)
				print('      %-91s|' % name_field)

				return t.print_fields(self._offset + offset, expected, indent + 1, prof, cache_lines)
			else:

				# a base class with no members. don't waste space by printing it
				if self._name == '<base-class>':
					return self._offset + offset + t.size()

				num_printed = 0
				while len(prof) > 0 and prof[0][0] < self._offset + offset + t.size():
					cnt = prof[0][1]
					member_offset = prof[0][0] - self._offset - offset
					if member_offset != 0: moff = '%+d' % member_offset
					else: moff = ''
					name_field = '%s%s%s' % ((' ' * indent), self._name, moff)
					if len(name_field) > 30: name_field = name_field[:30]

					cache_line = ''
					cache_line_prefix = ''
					if len(cache_lines) == 0 or cache_lines[-1] < (self._offset + offset) / cache_line_size:
						cache_line = '%scache-line %d' % (restore, (self._offset + offset) / cache_line_size)
						cache_line_prefix = cachecol
						cache_lines.append((self._offset + offset) / cache_line_size)

					print('%s%5d %-30s %s%8d: %s%s| %s' % ( \
						cache_line_prefix, \
						self._offset + offset, \
						name_field, \
						barcolor, cnt, \
						print_bar(cnt, prof_max), restore, \
						cache_line)
					)
					num_printed += 1
					del prof[0]
				if num_printed == 0:
					name_field = '%s%s' % ((' ' * indent), self._name)

					cache_line = ''
					cache_line_prefix = ''
					if len(cache_lines) == 0 or cache_lines[-1] < (self._offset + offset) / cache_line_size:
						cache_line = '%scache-line %d' % (restore, (self._offset + offset) / cache_line_size)
						cache_line_prefix = cachecol
						cache_lines.append((self._offset + offset) / cache_line_size)

					print('%s%5d %-91s| %s' % (cache_line_prefix, self._offset + offset, name_field, cache_line))

			return self._offset + offset + t.size()
		else:
			# normal struct layout mode
			if num_padding > 0:
				print('%s   --- %d Bytes padding --- %s%s' % (padcolor, num_padding, (' ' * 60), restore))
				expected = self._offset + offset

			if t.has_fields():
				print('     : %s[%s : %d] %s' % (('  ' * indent), t.name(), t.size(), self._name))
				return t.print_fields(self._offset + offset, expected, indent + 1, prof, cache_lines)
			else:

				cache_line = ''
				cache_line_prefix = ''
				if len(cache_lines) == 0 or cache_lines[-1] < (self._offset + offset) / cache_line_size:
					cache_line = ' -- {cache-line %d}%s' % ((self._offset + offset) / cache_line_size, restore)
					cache_line_prefix = cachecol
					cache_lines.append((self._offset + offset) / cache_line_size)

				l = '%5d: %s[%s : %d] %s' % (self._offset + offset, ('  ' * indent), t.name(), t.size(), self._name)
				print('%s%-*s%s' % (cache_line_prefix, terminal_width - len(cache_line) - 1, l, cache_line))
				return self._offset + offset + t.size()

class DwarfStructType(DwarfBase):

	def __init__(self, item, scope, types):
		self._scope = scope
		self._types = types
		self._declaration = 'AT_declaration' in item['fields']

		if 'AT_declaration' in item['fields']:
			self._size = 0
		else:
			self._size = int(item['fields']['AT_byte_size'], 16)

		if 'AT_name' in item['fields']:
			self._name = item['fields']['AT_name']
		else:
			self._name = '(anonymous)'

		self._fields = []
		if not 'children' in item: return

		try:
			for m in item['children']:
				if m['tag'] != 'TAG_member' \
					and m['tag'] != 'TAG_inheritance': continue
				if not 'AT_data_member_location' in m['fields']:
					continue

				self._fields.append(DwarfMember(m, types))
		except Exception as e:
			print('EXCEPTION! %s: ' % self._name , e)
			pass

		self._fields = sorted(self._fields, key=attrgetter('_offset'))

	def size(self):
		return self._size

	def name(self):
		return self._name

	def full_name(self):
		return '%s::%s' % (self._scope, self._name)

	def print_struct(self):
		if self._declaration: return

		global structcolor
		global restore
		global padcolor
		global profile

		prof = None
		if profile != None:
			prof_name = '%s::%s' % (self._scope, self._name)
			cnts = profile[prof_name[2:]]
			if cnts != None:
				prof = []
				for k, v in cnts.items():
					# don't show access counters < 1% of max
					if v < prof_max / 100: continue
					prof.append((k, v))
				prof = sorted(prof)

		print('\nstruct %s%s::%s%s [%d Bytes]' % (structcolor, self._scope, self._name, restore, self._size))
		expected = self.print_fields(0, 0, 0, prof, [])

		if profile == None:
			num_padding = (self._size) - expected
			if num_padding > 0:
				print('%s   --- %d Bytes padding --- %s%s' % (padcolor, num_padding, (' ' * 60), restore))

	def print_fields(self, offset, expected, indent, prof, cache_lines):
		for f in self._fields:
			expected = max(expected, f.print_field(offset, expected, indent, prof, cache_lines))
		return expected

	def has_fields(self):
		if len(self._fields) > 0: return True
		else: return False

	def match(self, f):
		if self._declaration: return False

		typename = '%s::%s' % (self._scope, self._name)

		global profile
		if profile != None:
			# strip the :: prefix to match the names in the profile
			name = typename[2:]
			return name in profile

		global show_standard_types
		if not show_standard_types:
			if typename.startswith('::std::'): return False
			if typename.startswith('::__gnu_cxx::'): return False
			if typename.startswith('::__'): return False
		if len(f) == 0: return True
		return typename.startswith(f)

class DwarfUnionType(DwarfStructType):

	def name(self):
		return 'union ' + DwarfStructType.name(self)

	def print_struct(self):
		print('\nunion %s::%s [%d Bytes]' % (self._scope, self._name, self._size))
		self.print_fields(0, 0, 0, None, [])

class DwarfMemberPtrType(DwarfTypedef):

	def __init__(self, item, scope, types):
		DwarfTypedef.__init__(self, item, scope, types)
		self._class_type = item['fields']['AT_containing_type']

	def size(self):
		global pointer_size
		return pointer_size

	def name(self):
		return '%s (%s::*)' % (self._types[self._underlying_type].name(), self._types[self._class_type].name())

	def match(self, f): return False

tag_to_type = {
	'TAG_base_type': DwarfBaseType,
	'TAG_pointer_type': DwarfPointerType,
	'TAG_reference_type': DwarfReferenceType,
	'TAG_rvalue_reference_type': DwarfRVReferenceType,
	'TAG_typedef': DwarfTypedef,
	'TAG_array_type': DwarfArrayType,
	'TAG_const_type': DwarfConstType,
	'TAG_volatile_type': DwarfVolatileType,
	'TAG_structure_type': DwarfStructType,
	'TAG_class_type': DwarfStructType,
	'TAG_ptr_to_member_type': DwarfMemberPtrType,
	'TAG_enumeration_type': DwarfEnumType,
	'TAG_subroutine_type': DwarfFunPtrType,
	'TAG_union_type': DwarfUnionType,
	'TAG_unspecified_type': DwarfVoidType,
}

DwarfCompilationUnit = namedtuple('DwarfCompilationUnit', ['addr_size', 'children'])
DwarfDie = namedtuple('DwarfDie', ['address', 'tag', 'attributes', 'children'])

DwarfAttributeOp = namedtuple('DwarfAttributeOp', ['opcode', 'extra'])
DwarfAttributeVal = namedtuple('DwarfAttributeVal', ['code'])

class DwarfAttributeRef(namedtuple('DwarfAttributeRef', ['address', 'address_map'])):
	@property
	def target(self):
		return self.address_map[self.address]

	def __repr__(self):
		return f'DwarfAttributeRef(address = {self.address!r}, address_map = {{...}})'

_DwarfRawDie = namedtuple('_DwarfRawDie', ['address', 'indent', 'tag', 'attributes']) 
_DwarfRawAttributeRef = namedtuple('_DwarfRawAttributeRef', ['address', 'hint'])

@parsy.generate
def dwarfdump():
	import parsy as p

	def dbg(parser):
		return parser.mark().map(lambda x: print(repr(x)))

	newline = p.regex(r'[\r\n]').desc('newline')
	newlines = newline.times(min = 1).desc('newlines')
	blank_line = newline.times(min = 2).desc('blank line')
	rest_of_line = p.regex(r'.*$', flags = re.MULTILINE)

	quoted_string = p.string('"') >> p.regex(r'[^"]*') << p.string('"')
	hex_number = p.regex(r'0x[0-9a-fA-F]+').map(lambda x: int(x, 0)).desc('hex number')
	decimal_number = p.regex(r'-?[0-9]+').map(lambda x: int(x, 0)).desc('decimal number')
	boolean = (p.string('true') | p.string('false')).map(lambda b: b == 'true').desc('boolean')
	dwarf_code = p.string('DW_') >> p.regex(r'\w+')

	null = p.string('NULL')

	attribute_contents = p.alt(
		quoted_string,
		p.seq(hex_number, p.whitespace >> quoted_string).combine(_DwarfRawAttributeRef),
		hex_number,
		decimal_number,
		boolean,
		p.seq(p.string('DW_') >> p.regex(r'OP_\w+'), (p.whitespace >> (hex_number | decimal_number)).optional()).combine(DwarfAttributeOp),
		dwarf_code.map(DwarfAttributeVal),
	)

	attribute = p.seq(
		p.whitespace >> dwarf_code,
		p.whitespace >> p.string('(') >> attribute_contents << p.string(')'),
	)

	die = p.seq(
		address = hex_number << p.string(': '),
		indent = p.regex('(  )*').map(lambda i: len(i) // 2),
		tag = null | dwarf_code,
		attributes = (p.string('\n') >> attribute).many().map(dict),
	).combine_dict(_DwarfRawDie)

	compilation_unit = p.seq(
		addr_size = (p.regex(r'.*addr_size = ') >> hex_number << rest_of_line).desc('compilation unit header'),
		children = blank_line >> die.sep_by(blank_line, min = 1),
	).combine_dict(DwarfCompilationUnit)

	return (yield (
		p.regex(r'.*:\s*file format.*\n\n') >>
		p.regex(r'.*\.debug_info contents:.*\n') >>
		compilation_unit.sep_by(blank_line) << newline.many()
	).many())

def combine_dies(file):
	address_map = {}
	for cu in file:
		stack = [DwarfCompilationUnit(addr_size = cu.addr_size, children = [])]

		for raw_die in cu.children:
			if raw_die.tag == 'NULL':
				continue

			if raw_die.indent > (len(stack) - 1):
				stack.append(stack[-1].children[-1])
			elif raw_die.indent < (len(stack) - 1):
				stack.pop()

			die = DwarfDie(
				address = raw_die.address,
				tag = raw_die.tag,
				attributes = {
					k: (DwarfAttributeRef(v.address, address_map) if isinstance(v, _DwarfRawAttributeRef) else v)
					for (k, v)
					in raw_die.attributes.items()
				},
				children = [],
			)
			address_map[die.address] = die

			stack[-1].children.append(die)

		yield stack[0], address_map

if __name__ == '__main__':
	import sys

	result = dwarfdump.parse(sys.stdin.read())
	files = [list(combine_dies(file)) for file in result]

	print(files)

	#ast.walk({object: print})
