import math
import struct

STRUCT_HEADER = '<'
WORD = 'q'
WORD_SIZE = struct.calcsize(f'{WORD}')
WORD_ALIGN = int(math.log2(WORD_SIZE))
WORD_MIN = -2 ** (WORD_SIZE * 8 -1)
WORD_ASM = f'.{WORD_SIZE}byte'

_WORD_ALIGN_BITS = 2**WORD_ALIGN - 1

def pad_size(size):
	return ((size - 1) | _WORD_ALIGN_BITS) + 1

def pad(s):
	return s + b'\x00' * (pad_size(len(s)) - len(s))
