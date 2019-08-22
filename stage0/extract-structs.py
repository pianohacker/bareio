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

from bareio import target

@dataclass
class Generator:
	def sanitize(self, name):
		return f'{name}_' if keyword.iskeyword(name) else name

	@property
	def sanitized_name(self):
		return self.sanitize(self.name)

@dataclass
class ContainerGenerator(Generator):
	children: List[Generator] = dataclass_field(default_factory = lambda: [])

	def add_child(self, child: Generator):
		self.children.append(child)

	def compile_initializers(self, indent):
		return '\n'.join(child.compile_initializers(indent) for child in self.children)

@dataclass
class StructGenerator(ContainerGenerator):
	name: str = ''
	field_names: Set[str] = dataclass_field(default_factory = lambda: set())

	def compile(self):
		return (
f'''class {self.sanitized_name}:
	def __init__(self, *, {self.compile_arguments()}):
		self.label = _get_label(f"{self.name}")
{self.compile_initializers(2)}
	
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
	is_pointer: bool

	def compile_arguments(self):
		if self.is_pointer:
			return f'''{self.sanitized_name} = 0'''
		else:
			return self.name

	def compile_compilers(self, indent):
		if self.is_pointer:
			value_expr = f'''getattr(self.{self.sanitized_name}, "label", self.{self.sanitized_name})'''
		else:
			value_expr = f'''self.{self.sanitized_name}'''

		return '\t' * indent + f'''print(f'.{self.width}byte {{{value_expr}}}')'''

@dataclass
class StringGenerator(DataGenerator):
	def compile_compilers(self, indent):
		return (
			'\t' * indent + f'''print('.ascii "' + _escape_str(self.{self.sanitized_name}) + '"')\n''' +
			'\t' * indent + f'''print('.align {target.WORD_SIZE}')'''
		)

@dataclass
class NumListGenerator(DataGenerator):
	is_pointer: bool

	def compile_compilers(self, indent):
		if self.is_pointer:
			value_expr = f'''getattr(elem, "label", elem)'''
		else:
			value_expr = f'''elem'''

		return (
			'\t' * indent + f'''for elem in self.{self.sanitized_name}:\n''' +
			'\t' * (indent + 1) + f'''print({value_expr})\n'''
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

for filename in sys.argv[1:]:
	pahole_result = list(enumerate(
		line.rstrip('\n')
		for line
		in subprocess.run(
			['pahole', '--anon_include', '--expand_types', filename],
			check=True,

			stdout=subprocess.PIPE,
			text=True,
		).stdout.split('\n')
	))

	structs = [
		(i, m)
		for (i, m)
		in (
			(i, struct_def_start_pattern.match(line))
			for (i, line)
			in pahole_result
		)
		if m
	]

	for i, match in structs:
		name = match.group(1)

		stack = [StructGenerator()]
		field_names = set()

		for j, line in pahole_result[i+1:]:
			end_match = struct_def_end_pattern.match(line)
			if end_match:
				if end_match.group(1):
					name = end_match.group(1)

				break

			orig_line = line
			line = re.sub(r'/\*[^*]*\*/', '', line).rstrip()

			if not line: continue

			words = line.split()

			if words[0] == 'union':
				stack.append(UnionGenerator())
				continue
			elif words[0] == '};':
				nested = stack.pop()
				stack[-1].add_child(nested)

				continue

			# TODO padding?
			width_match = width_pattern.search(orig_line)
			if not width_match:
				continue

			width = int(width_match.group(1))

			if width == 0:
				if words[0] == 'char' and words[-1].endswith('[];'):
					field = StringGenerator(name = words[-1][:-3])
				else:
					field = NumListGenerator(
						name = words[-1][:-3],
						is_pointer = words[-2] == '*',
					)
			else:
				field = NumGenerator(
					name = words[-1].rstrip(';'),
					is_pointer = words[-2] == '*',
					width = width,
				)

			field_names.add(field.name)
			stack[-1].add_child(field)

		if not name:
			print(f'WARN: could not find name of struct starting on line: f{i + 1}', file=sys.stderr)
			break

		if len(stack) != 1:
			raise RuntimeError(f'Unclosed container from parsing: ' + "\n".join(line for (i, line) in pahole_result[i:j+1]))

		stack[0].name = name.lstrip('_')
		stack[0].field_names = field_names

		print(stack[0].compile())
