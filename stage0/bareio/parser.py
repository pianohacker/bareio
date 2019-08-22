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
		return super().walk(
			handlers,
			[child.walk(handlers, *args) for child in self.children],
			*args,
		)

class Script(ASTContainerNode, namedtuple('Script', ['children'])):
	pass

@generate
def script():
	return (yield _message.many().map(Script))

class String(ASTNode, namedtuple('String', ['contents'])):
	pass

_string = (string('"') >> regex(r'[^"]*').map(String) << string('"')).desc('string')

class Integer(ASTNode, namedtuple('Integer', ['value'])):
	pass

_integer = regex(r'-?(0|([1-9][0-9]*))').map(lambda i: Integer(int(i))).desc('integer')

class NamedMessage(ASTContainerNode, namedtuple('NamedMessage', ['name', 'children'])):
	pass

_named_message = seq(
	name = regex(r'[^ \t\n\r(),]+'),
	children = (lexeme('(') >> script.sep_by(lexeme(',')) << lexeme(')')).times(0, 1).map(lambda v: v[0] if v else []),
).combine_dict(NamedMessage)

class ResetContext(ASTNode, namedtuple('ResetContext', [])):
	pass

_reset_context = string("\n").map(lambda _: ResetContext())

_message = lexeme(alt(
	_string,
	_integer,
	_named_message,
	_reset_context,
))

if __name__ == '__main__':
	import sys

	ast = script.parse(sys.stdin.read())

	print(ast)

	ast.walk({object: print})
