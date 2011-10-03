"""
Apwal common exceptions
"""

class FileNotFound(Exception):
	"""
	File not found exception
	"""
	pass

class InternalRedirect(Exception):
	"""
	Internal redirect
	"""
	def __init__(self, destination):
		Exception.__init__(self)
		self.redirect_to = destination
	
	def getDestination(self):
		return self.redirect_to

class ExternalRedirect(InternalRedirect):
	"""
	External redirect
	"""
	pass

class ForbiddenAccess(Exception):
	pass