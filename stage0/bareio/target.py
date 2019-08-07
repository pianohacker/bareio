import struct

STRUCT_HEADER = '<'
INT = 'q'
INT_MIN = -2 ** (struct.calcsize(f'{STRUCT_HEADER}{INT}') * 8 -1)
