from dataclasses import dataclass, field
import sys
from typing import Optional, Union

from bareio import target

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

messages = []
objects = []
strings = []

print('.section .data')
print('.global _builtin_messages')
print('_builtin_messages:')

for line in sys.stdin:
	for message in line.split():
		if message in method_offsets:
			m = structs.BareioMessage(
				name_offset = method_offsets[message],
				forced_result = 0,
			)
		elif message.isdecimal() or (message.startswith('-') and message[1:].isdecimal()):
			o = structs.BareioObject(
				data_integer = int(message),
				builtin_dispatch = '_bareio_builtin_integer_dispatch',
			)
			objects.append(o)
			m = structs.BareioMessage(
				name_offset = 0,
				forced_result = o,
			)
		elif message.startswith('"') and message.endswith('"'):
			s = structs.BareioString(len = len(message) - 2, contents = message[1:-1])
			strings.append(s)
			o = structs.BareioObject(
				data_string = s,
				builtin_dispatch = '_bareio_builtin_string_dispatch',
			)
			objects.append(o)
			m = structs.BareioMessage(
				name_offset = 0,
				forced_result = o,
			)
		else:
			print(f'Warning: unknown message {message}', file=sys.stderr)
			continue

		m.compile()

	structs.BareioMessage(name_offset = MESSAGES_RESET_CONTEXT, forced_result = 0).compile()

structs.BareioMessage(name_offset = MESSAGES_END, forced_result = 0).compile()

for o in objects:
	o.compile()

for s in strings:
	s.compile()
