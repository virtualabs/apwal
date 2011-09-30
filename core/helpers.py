"""
Pywa decorators
"""

from types import *

__all__ = [
	'bind',
	'route',
	'main',
	'plug',
	'onerror',
]

class bind:
	"""
	Map a method to a given url
	"""
	def __init__(self, url):
		self.url = url
	
	def __call__(self, f):
		f.url = self.url
		return f

class Medias:
	"""
	Media directory and allowed extensions container
	"""
	def __init__(self, mediaDir, mediaTypes):
		if type(mediaTypes) is StrType:
			self.__media_types = [mediaTypes.upper()]
		elif type(mediaTypes) is ListType:
			self.__media_types = [mt.upper() for mt in mediaTypes]
		else:
			raise TypeError()
		self.__media_dir = mediaDir
		
	def getMediaDir(self):
		"""
		Retrieve media directory
		"""
		return self.__media_dir
		
	def getMediaTypes(self):
		"""
		Retrieve allowed media types (ext)
		"""
		return self.__media_types
		
	def isMediaTypeAllowed(self, mediaType):
		"""
		Check if a media type is allowed
		"""
		return (mediaType in self.__media_types)


class media:
	"""
	Decorates a method in order to associate a relative media directory and associated media types
	"""
	def __init__(self, relativeMediaDir, mediaTypes=None):
		"""
		Specify the media directory and allowed media types
		"""		
		self.__medias = Medias(relativeMediaDir, mediaTypes)
		
	def __call__(self, f):
		f.medias = self.__medias
		return f

class plug:
	def __init__(self, *kargs):
		self.__pluggables = []
		for p in kargs:
			if type(p) is TupleType:
				_p,_route = p
				_p.route = _route
				self.__pluggables.append(_p)
			else:
				self.__pluggables.append(p)
		
	def __call__(self, f):
		f.preplugs = self.__pluggables
		return f

def main(f):
	"""
	Decorates a class in order to mark it as a valid handler
	"""
	def wrap_handler(f):
		f.handler = True
		return f
	return wrap_handler(f)

def is_handler(c):
	if hasattr(c,'handler'):
		return getattr(c,'handler')==True
	else:
		return False

class onerror:
	def __init__(self, *kargs):
		self._error = [err_code for err_code in kargs]
	def __call__(self, f):
		f.onerror = self._error
		return f
		
class route:
	def __init__(self, route):
		self._route = route
	def __call__(self, c):
		c.route = self._route
		return c
