## Struct extractor
# Extracts struct definitions from debugging info of compiled C, and translates them into Python
# code that can be used to assemble the same structs.
#
# Not yet handled:
# * Padding
# * Unions with variable-width elements

from dataclasses import dataclass, field as dataclass_field
import keyword
import os
import subprocess
import re
import sys
from typing import Any, List, Set

from bareio import llvm_dwarfdump, target, utils

@dataclass
class Generator:
	def sanitize(self, name):
		return f'{name}_' if keyword.iskeyword(name) else name

	@property
	def sanitized_name(self):
		return self.sanitize(self.name)

@dataclass
class ContainerGenerator(Generator):
	children: List[Generator]

	def add_child(self, child: Generator):
		self.children.append(child)

	def compile_initializers(self, indent):
		return '\n'.join(child.compile_initializers(indent) for child in self.children)

@dataclass
class StructGenerator(ContainerGenerator):
	name: str

	def compile(self):
		return (
f'''class {self.sanitized_name}:
	def __init__(self, *, {self.compile_arguments()}):
		self.label = _get_label(f"{self.name}")
{self.compile_initializers(2)}

	def __repr__(self):
		return f'{self.name}({{vars(self)}})'
	
	def compile(self):
		print(f'{{self.label}}:')

{self.compile_compilers(2)}
'''
		)

	def compile_arguments(self):
		return ', '.join(child.compile_arguments() for child in self.children)

	def compile_compilers(self, indent):
		return '\n\n'.join(child.compile_compilers(indent) for child in self.children)

@dataclass
class UnionGenerator(ContainerGenerator):
	def compile_arguments(self):
		return ', '.join(f'{self.sanitize(child.name)} = None' for child in self.children)

	def compile_compilers(self, indent):
		return '\n'.join(
			'\t' * indent + f'''{'el' if i > 0 else ''}if self.{self.sanitize(child.name)} is not None:
{child.compile_compilers(indent + 1)}'''
			for (i, child)
			in enumerate(self.children)
		)

@dataclass
class DataGenerator(Generator):
	name: str

	def compile_arguments(self):
		return self.sanitized_name

	def compile_initializers(self, indent):
		return '\t' * indent + f'self.{self.sanitized_name} = {self.sanitized_name}'

@dataclass
class NumGenerator(DataGenerator):
	width: int

	def compile_compilers(self, indent):
		return '\t' * indent + f'''print(f'.{self.width}byte {{self.{self.sanitized_name}}}')'''

@dataclass
class PointerGenerator(DataGenerator):
	width: int

	def compile_arguments(self):
		return f'''{self.sanitized_name} = 0'''

	def compile_compilers(self, indent):
		return '\t' * indent + f'''print(f'.{self.width}byte {{getattr(self.{self.sanitized_name}, "label", self.{self.sanitized_name})}}')'''

@dataclass
class StringGenerator(DataGenerator):
	def compile_compilers(self, indent):
		return (
			'\t' * indent + f'''print('.ascii "' + _escape_str(self.{self.sanitized_name}) + '"')\n''' +
			'\t' * indent + f'''print('.align {target.WORD_SIZE}')'''
		)

@dataclass
class PointerListGenerator(DataGenerator):
	width: int

	def compile_compilers(self, indent):
		return (
			'\t' * indent + f'''for elem in self.{self.sanitized_name}:\n''' +
			'\t' * (indent + 1) + f'''print(f'.{self.width}byte {{getattr(elem, "label", elem)}}')'''
		)

@dataclass
class DataListGenerator(DataGenerator):
	def compile_compilers(self, indent):
		value_expr = f''''''

		return (
			'\t' * indent + f'''for elem in self.{self.sanitized_name}:\n''' +
			'\t' * (indent + 1) + f'''elem.compile()'''
		)

struct_def_start_pattern = re.compile(r'^(?:typedef )?struct(?: (\S+))? \{')
struct_def_end_pattern = re.compile(r'^\}(?: (\S+))?;')
width_pattern = re.compile(r'\/\*\s*\d+\s*(\d+)\s*\*\/\s*$')

print(f'''
def _get_label(prefix):
	result = _get_label.next
	_get_label.next += 1

	return f'{{prefix}}_{{result}}'

_get_label.next = 0

def _escape_str(s):
	return s.encode('utf-8').decode('latin-1').encode('unicode_escape').decode('latin-1')

''')


structs = llvm_dwarfdump.collect_structs(
	subprocess.run(
		['llvm-dwarfdump', '--debug-info'] + sys.argv[1:],
		check=True,

		stdout=subprocess.PIPE,
		text=True,
	).stdout
)

def _generate_struct(walker, struct):
	return StructGenerator(
		name = struct.name,
		children = list([x for x in walker.walk_all(struct.children) if x]),
	)

def _generate_value(walker, value):
	return NumGenerator(
		name = value.name,
		width = value.width,
	)

def _generate_pointer(walker, value):
	return PointerGenerator(
		name = value.name,
		width = value.width,
	)

def _generate_flexible_struct_array(walker, value):
	return DataListGenerator(
		name = value.name,
	)

def _generate_flexible_value_array(walker, value):
	if value.type == 'char':
		return StringGenerator(
			name = value.name
		)
	else:
		raise RuntimeError(f'unhandled flexible array type: {value.type}')

def _generate_flexible_pointer_array(walker, value):
	return PointerListGenerator(
		name = value.name,
		width = value.width,
	)

def _generate_union(walker, union):
	return UnionGenerator(
		children = list([x for x in walker.walk_all(union.children) if x]),
	)

for struct in structs.values():
	print(
		utils.walker({
			llvm_dwarfdump.DwarfStruct: _generate_struct,
			llvm_dwarfdump.DwarfMemberValue: _generate_value,
			llvm_dwarfdump.DwarfMemberPointer: _generate_pointer,
			llvm_dwarfdump.DwarfMemberFlexibleStructArray: _generate_flexible_struct_array,
			llvm_dwarfdump.DwarfMemberFlexibleValueArray: _generate_flexible_value_array,
			llvm_dwarfdump.DwarfMemberFlexiblePointerArray: _generate_flexible_pointer_array,
			llvm_dwarfdump.DwarfMemberUnion: _generate_union,
		}).walk(struct).compile()
	)
