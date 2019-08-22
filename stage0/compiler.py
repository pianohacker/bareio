from collections import deque
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

pending = deque()

print('.section .data')
print('.global _builtin_script')
print('_builtin_script:')

def handle_named_message(message, argument_scripts):
	arguments = 0

	if argument_scripts:
		for a in argument_scripts:
			pending.append(a)

		arguments = structs.BareioArguments(
			len = len(argument_scripts),
			members = argument_scripts,
		)
		pending.append(arguments)
	
	return structs.BareioMessage(
		name_offset = method_offsets[message.name],
		arguments = arguments,
	)

def handle_string(string):
	s = structs.BareioString(len = len(string.contents), contents = string.contents)
	pending.append(s)
	o = structs.BareioObject(
		data_string = s,
		builtin_lookup = '_bareio_builtin_string_lookup',
	)
	pending.append(o)

	return structs.BareioMessage(name_offset = 0, forced_result = o)

def handle_integer(integer):
	o = structs.BareioObject(
		data_integer = integer.value,
		builtin_lookup = '_bareio_builtin_integer_lookup',
	)
	pending.append(o)

	return structs.BareioMessage(name_offset = 0, forced_result = o)

def handle_reset_context(_):
	return structs.BareioMessage(name_offset = MESSAGES_RESET_CONTEXT)

def handle_script(_, messages):
	return structs.BareioScript(
		messages = messages + [structs.BareioMessage(name_offset = MESSAGES_END)],
	)

parser.script.parse(sys.stdin.read()).walk({
	parser.NamedMessage: handle_named_message,
	parser.String: handle_string,
	parser.Integer: handle_integer,
	parser.ResetContext: handle_reset_context,
	parser.Script: handle_script,
}).compile()

while pending:
	pending.popleft().compile()
