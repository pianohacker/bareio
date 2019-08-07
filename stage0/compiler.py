import struct
import sys

from bareio import target

if sys.version_info[0] < 3:
	print('Python 3.0+ required', file=sys.stderr)
	sys.exit(1)

if sys.stdout.isatty():
	print('Cowardly refusing to output to a tty', file=sys.stderr)
	sys.exit(1)

MESSAGE_STRUCT = struct.Struct(f'{target.STRUCT_HEADER}{target.INT}')
BUILTIN_MESSAGE_BASE = target.INT_MIN
HALT = -1

def output_packed(struct_, *args):
	sys.stdout.buffer.write(struct_.pack(*args))

method_offsets = {
	method_name.strip(): BUILTIN_MESSAGE_BASE + i
	for i, method_name
	in enumerate(open('src/method-names.lock'))
}

for message in sys.stdin.read().split():
	if message in method_offsets:
		output_packed(MESSAGE_STRUCT, method_offsets[message])
	else:
		print('Warning: unknown message {message}', file=sys.stderr)

output_packed(MESSAGE_STRUCT, HALT)

sys.stdout.flush()
