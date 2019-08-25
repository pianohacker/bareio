class walker:
	def __init__(self, _handlers, **kwargs):
		self._handlers = _handlers
		self.__dict__.update(kwargs)

	def walk_all(self, children, **kwargs):
		for child in children:
			yield self.walk(child, **kwargs)
	
	def walk(self, tree, **kwargs):
		for type, handler in self._handlers.items():
			if isinstance(tree, type):
				return handler(self, tree, **kwargs)
