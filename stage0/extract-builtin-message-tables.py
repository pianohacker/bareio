from collections import OrderedDict
import os
import re
import sys
import tempfile

from bareio import target

## Patterns
message_decl_pattern = re.compile(r'^BAREIO_MESSAGE\("([^"]+)", "([^"]+)"\)')
func_disallowed_chars_pattern = re.compile(r'^[^A-Za-z_]|[^A-Za-z0-9_]')

## Setup
# Check Python version and arguments.
if sys.version_info[0] < 3:
	print('Python 3.0+ required', file=sys.stderr)
	sys.exit(1)

if len(sys.argv) < 4:
	print(f'Usage {sys.argv[0]} LOCK_FILE OUTPUT_DIR INPUT_FILE...', file=sys.stderr)
	sys.exit(1)

lock_file_name = sys.argv[1]
out_dir = sys.argv[2]
input_files = sys.argv[3:]

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

for input_file in input_files:
	for i, line in enumerate(open(input_file)):
		result = message_decl_pattern.match(line)

		if not result: continue

		context, message_name = result.groups()
		
		contexts.add(context)
		message_contexts.setdefault(message_name, set()).add(context)

## Output

# First, we create our output directory if needed, then remove anything in it.
os.makedirs(out_dir, exist_ok = True)
for output in os.listdir(out_dir):
	os.unlink(os.path.join(out_dir, output))

# We write to the lock file by outputting to a tempfile, then renaming over.
lock_file_out = tempfile.NamedTemporaryFile(
	dir = os.path.dirname(lock_file_name),
	prefix = '.method-offsets.lock',

	mode = 'w',
	encoding = 'utf-8',

	delete = False,
)

### Jump table writing
context_outputs = {}

for context in contexts:
	context_outputs[context] = context_output = open(
		os.path.join(out_dir, context + ".c"),
		"w",
		encoding = "utf-8",
	)

	context_output.write('\tswitch (message->name_offset) {\n')

BUILTIN_MESSAGE_BASE = target.INT_MIN

for i, message in enumerate(message_contexts.items()):
	message_name, contexts = message

	lock_file_out.write(f'{message_name}\n')

	message_offset = BUILTIN_MESSAGE_BASE + i

	for context in contexts:
		func_name = func_disallowed_chars_pattern.sub('_', f'bareio_builtin_{context}_{message_name}')

		# We have to encode the message code oddly, because -INT_MIN is parsed as -(INT_MIN), and
		# INT_MIN is out of range for signed ints.
		context_outputs[context].write(
			f'\t\tcase {message_offset + 1} -1: message_func = (BareioBuiltinMessageFunc*){func_name}; break;\n'
		)

for context, context_output in context_outputs.items():
	context_output.write('\t}\n')
	context_output.close()

try:
	os.rename(lock_file_out.name, lock_file_name)
except OSError:
	os.unlink(lock_file_out.name)
