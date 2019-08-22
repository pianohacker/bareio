from collections import namedtuple
from parsy import *

def lexeme(p):
    """
    From a parser (or string), make a parser that consumes
    whitespace on either side.
    """
    if isinstance(p, str):
        p = string(p)
    return regex(r'[ \t]*') >> p << regex(r'[ \t]*')

class ASTNode:
	def walk(self, handlers, *args):
		for type, handler in handlers.items():
			if isinstance(self, type):
				return handler(self, *args)

class ASTContainerNode(ASTNode):
	def walk(self, handlers, *args):
		super().walk(
			handlers,
			[child.walk(handlers, *args) for child in self.children],
			*args,
		)

class String(ASTNode, namedtuple('String', ['contents'])):
	pass

_string = string('"') >> regex(r'[^"]*').map(lambda s: String(s)) << string('"')

class Integer(ASTNode, namedtuple('Integer', ['value'])):
	pass

_integer = regex(r'-?(0|([1-9][0-9]*))').map(lambda i: Integer(int(i)))

class NamedMessage(ASTNode, namedtuple('NamedMessage', ['name'])):
	pass

_named_message = regex(r'\S+').map(lambda n: NamedMessage(n))

class ResetContext(ASTNode, namedtuple('ResetContext', [])):
	pass

_reset_context = string("\n").map(lambda _: ResetContext())

class Messages(ASTContainerNode, namedtuple('Messages', ['children'])):
	pass

_message = lexeme(alt(
	_string,
	_integer,
	_named_message,
	_reset_context,
))

messages = _message.many().map(lambda m: Messages(m))

if __name__ == '__main__':
	import sys

	ast = messages.parse(sys.stdin.read())

	print(ast)

	ast.walk({object: print})
