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
