from collections import OrderedDict
import os
import re
import sys
import tempfile

from bareio import target

## Patterns
message_decl_pattern = re.compile(r'^BAREIO_MESSAGE\(([^,]+), ([^)]+)\)')
func_disallowed_chars_pattern = re.compile(r'^[^A-Za-z_]|[^A-Za-z0-9_]')

## Setup
# Check Python version and arguments.
if sys.version_info[0] < 3:
	print('Python 3.0+ required', file=sys.stderr)
	sys.exit(1)

if len(sys.argv) != 2:
	print(f'Usage {sys.argv[0]} LOCK_FILE', file=sys.stderr)
	sys.exit(1)

lock_file_name = sys.argv[1]

### Read lock file
# The lock file fixes both the known methods and their order, so that as message names are added and
# removed, builtin message offsets stay constant.

contexts = set()
message_contexts = OrderedDict()

try:
	for message in open(lock_file_name):
		message_contexts[message.strip()] = set()
except OSError:
	pass

## C parsing

for line in sys.stdin:
	result = message_decl_pattern.match(line)

	if not result: continue

	context, message_name = result.groups()
	
	contexts.add(context)
	message_contexts.setdefault(message_name, set()).add(context)

## Output
# We write to the lock file by outputting to a tempfile, then renaming over.
lock_file_out = tempfile.NamedTemporaryFile(
	dir = os.path.dirname(lock_file_name),
	prefix = '.method-offsets.lock',

	mode = 'w',
	encoding = 'utf-8',

	delete = False,
)

### Header
print('''
#include <stddef.h>

#include "bio-types.h"
''')

### Jump table writing
context_results = {}

for context in contexts:
	context_results[context] = f'BareioBuiltinMessageFunc* _bareio_builtin_{context}_lookup(ptrdiff_t name_offset) {{\n'
	context_results[context] += '\tswitch (name_offset) {\n'

BUILTIN_MESSAGE_BASE = target.WORD_MIN

for i, message in enumerate(message_contexts.items()):
	message_name, contexts = message

	lock_file_out.write(f'{message_name}\n')

	message_offset = BUILTIN_MESSAGE_BASE + i

	for context in contexts:
		func_name = func_disallowed_chars_pattern.sub('_', f'bareio_builtin_{context}_{message_name}')

		context_results[context] = f'extern BareioBuiltinMessageFunc {func_name};\n' + context_results[context]

		# We have to encode the message code oddly, because -WORD_MIN is parsed as -(WORD_MIN), and
		# WORD_MIN is out of range for signed ints.
		context_results[context] += f'\t\tcase {message_offset + 1} -1: return {func_name};\n'

for context, context_output in context_results.items():
	context_results[context] += '\t}\n'
	context_results[context] += '\n'
	context_results[context] += '\treturn 0;\n'
	context_results[context] += '}\n'

	print(context_results[context])

try:
	os.rename(lock_file_out.name, lock_file_name)
except OSError:
	os.unlink(lock_file_out.name)
