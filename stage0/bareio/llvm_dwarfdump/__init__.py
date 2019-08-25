from collections import namedtuple

from . import parser

DwarfStruct = namedtuple('DwarfStruct', ['name', 'children'])
DwarfMemberValue = namedtuple('DwarfMemberValue', ['name', 'width'])
DwarfMemberPointer = namedtuple('DwarfMemberPointer', ['name', 'width'])
DwarfMemberUnion = namedtuple('DwarfMemberUnion', ['children'])
DwarfMemberFlexibleStructArray = namedtuple('DwarfMemberFlexibleStructArray', ['name', 'type', 'width'])
DwarfMemberFlexibleValueArray = namedtuple('DwarfMemberFlexibleValueArray', ['name', 'type', 'width'])
DwarfMemberFlexiblePointerArray = namedtuple('DwarfMemberFlexiblePointerArray', ['name', 'type', 'width'])

def collect_structs(dwarfdump_output):
	def _resolve_typedefs(type):
		return typedef_targets.get(type.address, type)

	def _collect_union(die):
		members = []

		for member in die.children:
			members.append(_collect_member(member))

		return DwarfMemberUnion(members)

	def _collect_member(die):
		type = _resolve_typedefs(die.attributes['AT_type'].target)

		if type.tag == 'TAG_union_type':
			return _collect_union(type)
		elif type.tag == 'TAG_pointer_type':
			return DwarfMemberPointer(
				die.attributes['AT_name'],
				type.attributes['AT_byte_size'],
			)
		elif type.tag == 'TAG_array_type':
			member_type = _resolve_typedefs(type.attributes['AT_type'].target)

			if member_type.tag == 'TAG_pointer_type':
				member_pointed_type = _resolve_typedefs(type.attributes['AT_type'].target)
				return DwarfMemberFlexiblePointerArray(
					die.attributes['AT_name'],
					member_pointed_type.attributes.get('AT_name', 'void'),
					member_type.attributes['AT_byte_size'],
				)
			elif member_type.tag == 'TAG_structure_type':
				return DwarfMemberFlexibleStructArray(
					die.attributes['AT_name'],
					typedef_referrers.get(member_type.address, [member_type])[0].attributes['AT_name'],
					member_type.attributes['AT_byte_size'],
				)
			else:
				return DwarfMemberFlexibleValueArray(
					die.attributes['AT_name'],
					member_type.attributes['AT_name'],
					member_type.attributes['AT_byte_size'],
				)
		else:
			return DwarfMemberValue(
				die.attributes['AT_name'],
				type.attributes['AT_byte_size'],
			)

	def _collect_struct(die):
		struct_name = die.attributes.get('AT_name', None)

		if die.address in typedef_referrers:
			struct_name = typedef_referrers[die.address][0].attributes['AT_name']

		members = []

		for member in die.children:
			members.append(_collect_member(member))

		return struct_name, DwarfStruct(struct_name, members)

	def _collect_structs_from_cu(cu):
		structs = {}

		for die in cu.children[0].children:
			if die.tag != 'TAG_structure_type':
				continue

			structs.__setitem__(*_collect_struct(die))
		
		return structs

	structs = {}

	result = parser.dwarfdump.parse(dwarfdump_output)

	for file in result:
		for cu, address_map in parser.combine_dies(file):
			assert(len(cu.children) == 1)
			assert(cu.children[0].tag == 'TAG_compile_unit')

			typedef_referrers = {}
			typedef_targets = {}

			for die in cu.children[0].children:
				if die.tag != 'TAG_typedef':
					continue

				target = die

				while target.tag == 'TAG_typedef':
					target = target.attributes['AT_type'].target

				typedef_referrers.setdefault(target.address, []).append(die)
				typedef_targets[die.address] = target

			structs.update(_collect_structs_from_cu(cu))
	
	return structs
