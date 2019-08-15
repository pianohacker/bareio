from dataclasses import dataclass, field
import struct
import sys
from typing import Optional, Union

from bareio import target

if sys.version_info[0] < 3:
	print('Python 3.0+ required', file=sys.stderr)
	sys.exit(1)

BUILTIN_MESSAGE_BASE = target.WORD_MIN
MESSAGES_RESET_CONTEXT = -2
MESSAGES_END = -1

last_id = 0
def get_id():
	global last_id
	result = last_id
	last_id += 1
	return result

def escape_str(s):
	return s.encode('utf-8').decode('latin-1').encode('unicode_escape').decode('latin-1')

@dataclass()
class String:
	contents: bytes
	id: int = field(init = False)

	def __post_init__(self):
		self.id = get_id()

	@property
	def label(self):
		return f'_builtin_string_{self.id}'

	def compile(self):
		return f'''{self.label}:
	{target.WORD_ASM} {len(self.contents)}
	.ascii "{escape_str(self.contents)}"
	'''

@dataclass()
class Object:
	data: Union[String, int]
	id: int = field(init = False)

	def __post_init__(self):
		self.id = get_id()

	@property
	def label(self):
		return f'_builtin_object_{self.id}'

	def compile(self):
		return f'''{self.label}:
	{target.WORD_ASM} {"_bareio_builtin_string_dispatch" if isinstance(self.data, String) else "_bareio_builtin_integer_dispatch"}
	{target.WORD_ASM} {self.data.label if isinstance(self.data, String) else self.data}
	'''

@dataclass()
class Message:
	name_offset: int
	forced_result: Optional[Object] = None

	def compile(self):
		return f'''
	{target.WORD_ASM} {self.name_offset}
	{target.WORD_ASM} {self.forced_result.label if self.forced_result else 0}
	'''

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
			m = Message(name_offset = method_offsets[message])
		elif message.isdecimal() or (message.startswith('-') and message[1:].isdecimal()):
			o = Object(data = int(message))
			objects.append(o)
			m = Message(name_offset = 0, forced_result = o)
		elif message.startswith('"') and message.endswith('"'):
			s = String(contents = message[1:-1])
			strings.append(s)
			o = Object(data = s)
			objects.append(o)
			m = Message(name_offset = 0, forced_result = o)
		else:
			print(f'Warning: unknown message {message}', file=sys.stderr)
			continue

		print(m.compile())

	print(Message(name_offset = MESSAGES_RESET_CONTEXT).compile())

print(Message(name_offset = MESSAGES_END).compile())

for o in objects:
	print(o.compile())

for s in strings:
	print(s.compile())
