from dataclasses import dataclass, field
import sys
from typing import Optional, Union

from bareio import parser, target

import importlib.util
spec = importlib.util.spec_from_file_location('bareio.structs', 'build/structs.py')
structs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(structs)

if sys.version_info[0] < 3:
	print('Python 3.0+ required', file=sys.stderr)
	sys.exit(1)

BUILTIN_MESSAGE_BASE = target.WORD_MIN
MESSAGES_RESET_CONTEXT = -2
MESSAGES_END = -1

method_offsets = {
	method_name.strip(): BUILTIN_MESSAGE_BASE + i
	for i, method_name
	in enumerate(open('src/method-names.lock'))
}

objects = []
strings = []

print('.section .data')
print('.global _builtin_messages')
print('_builtin_messages:')

def handle_named_message(message):
	m = structs.BareioMessage(name_offset = method_offsets[message.name])
	m.compile()
	return m

def handle_string(string):
	s = structs.BareioString(len = len(string.contents), contents = string.contents)
	strings.append(s)
	o = structs.BareioObject(
		data_string = s,
		builtin_dispatch = '_bareio_builtin_string_dispatch',
	)
	objects.append(o)

	m = structs.BareioMessage(name_offset = 0, forced_result = o)
	m.compile()
	return m

def handle_integer(integer):
	o = structs.BareioObject(
		data_integer = integer.value,
		builtin_dispatch = '_bareio_builtin_integer_dispatch',
	)
	objects.append(o)

	m = structs.BareioMessage(name_offset = 0, forced_result = o)
	m.compile()
	return m

def handle_reset_context(_):
	m = structs.BareioMessage(name_offset = MESSAGES_RESET_CONTEXT)
	m.compile()
	return m

parser.messages.parse(sys.stdin.read()).walk({
	parser.NamedMessage: handle_named_message,
	parser.String: handle_string,
	parser.Integer: handle_integer,
	parser.ResetContext: handle_reset_context,
})

structs.BareioMessage(name_offset = MESSAGES_END).compile()

for o in objects:
	o.compile()

for s in strings:
	s.compile()
