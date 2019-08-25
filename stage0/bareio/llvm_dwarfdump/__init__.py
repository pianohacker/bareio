from collections import namedtuple

from . import parser

DwarfStruct = namedtuple('DwarfStruct', ['name', 'members'])
DwarfMemberValue = namedtuple('DwarfMemberValue', ['name', 'type', 'width'])
DwarfMemberPointer = namedtuple('DwarfMemberValue', ['name', 'type', 'width'])
DwarfMemberUnion = namedtuple('DwarfMemberUnion', ['members'])
DwarfMemberFlexibleArray = namedtuple('DwarfMemberFlexibleArray', ['name', 'type'])

def _collect_struct(die, address_map, typedef_referrers, typedef_targets):
	struct_name = die.attributes.get('AT_name', None)

	if die.address in typedef_referrers:
		struct_name = typedef_referrers[die.address][0].attributes['AT_name']

	print(f'{struct_name}')

	for member in die.children:
		print(f'  ' + member.attributes.get("AT_name", f'({member.tag})')) 

	print()

	return struct_name, DwarfStruct(struct_name, [])

def _collect_structs_from_cu(cu, address_map, typedef_referrers, typedef_targets):
	structs = {}

	for die in cu.children[0].children:
		if die.tag != 'TAG_structure_type':
			continue

		structs.__setitem__(*_collect_struct(die, address_map, typedef_referrers, typedef_targets))
	
	return structs

def collect_structs(dwarfdump_output):
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

			structs.update(_collect_structs_from_cu(cu, address_map, typedef_referrers, typedef_targets))
	
	return structs
