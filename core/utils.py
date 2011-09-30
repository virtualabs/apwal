from threading import local
from imp import find_module,load_module

try:
    # The mod_python version is more efficient, so try importing it first.
    from mod_python.util import parse_qsl
except ImportError:
    from cgi import parse_qsl

__all__ = [
	'ThreadStorage',
	'ThreadDict',
	'MultiValueDictKeyError',
	'MultiValueDict',
	'QueryDict',
	'parse_cookie',
	'load_tool',
]

class ThreadStorage(object):
	"""
	Thread local storage
	"""
	def __init__(self):
		self.__storage = local()
	
	def __getattr__(self, key):
		if key in self.__storage:
			return self.__storage[key]
		else:
			raise AttributeError()
	
	def __setitem__(self, key, value):
		self.__storage[key] = value	
	
	def __getitem__(self, key):
		if key in self.__storage:
			return self.__storage[key]
		else:
			raise IndexError()			
	
	def __setattr__(self, key, value):
		self.__storage[key] = value
		
	def __contains__(self, key):
		return key in self.__storage
		
	def __len__(self):
		return len(self.__storage)


class ThreadDict(ThreadStorage):
	"""
	Threaded dict
	"""
	def __init__(self):
		ThreadStorage.__init__(self)
		
	def __setitem__(self, key, value):
		self[key]=value
	
	def __getitem__(self, key):
		return self[key] 
		
	def __len__(self):
		return len(self)
		
	def __contains__(self, key):
		return key in self

class MultiValueDictKeyError(KeyError):
    pass

class MultiValueDict(dict):
    """
    A subclass of dictionary customized to handle multiple values for the same key.

    >>> d = MultiValueDict({'name': ['Adrian', 'Simon'], 'position': ['Developer']})
    >>> d['name']
    'Simon'
    >>> d.getlist('name')
    ['Adrian', 'Simon']
    >>> d.get('lastname', 'nonexistent')
    'nonexistent'
    >>> d.setlist('lastname', ['Holovaty', 'Willison'])

    This class exists to solve the irritating problem raised by cgi.parse_qs,
    which returns a list for every key, even though most Web forms submit
    single name-value pairs.
    """
    def __init__(self, key_to_list_mapping=()):
        dict.__init__(self, key_to_list_mapping)

    def __repr__(self):
        return "<MultiValueDict: %s>" % dict.__repr__(self)

    def __getitem__(self, key):
        """
        Returns the last data value for this key, or [] if it's an empty list;
        raises KeyError if not found.
        """
        try:
            list_ = dict.__getitem__(self, key)
        except KeyError:
            raise MultiValueDictKeyError, "Key %r not found in %r" % (key, self)
        try:
            return list_[-1]
        except IndexError:
            return []

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, [value])

    def __copy__(self):
        return self.__class__(dict.items(self))

    def __deepcopy__(self, memo=None):
        import copy
        if memo is None: memo = {}
        result = self.__class__()
        memo[id(self)] = result
        for key, value in dict.items(self):
            dict.__setitem__(result, copy.deepcopy(key, memo), copy.deepcopy(value, memo))
        return result

    def get(self, key, default=None):
        "Returns the default value if the requested data doesn't exist"
        try:
            val = self[key]
        except KeyError:
            return default
        if val == []:
            return default
        return val

    def getlist(self, key):
        "Returns an empty list if the requested data doesn't exist"
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return []

    def setlist(self, key, list_):
        dict.__setitem__(self, key, list_)

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def setlistdefault(self, key, default_list=()):
        if key not in self:
            self.setlist(key, default_list)
        return self.getlist(key)

    def appendlist(self, key, value):
        "Appends an item to the internal list associated with key"
        self.setlistdefault(key, [])
        dict.__setitem__(self, key, self.getlist(key) + [value])

    def items(self):
        """
        Returns a list of (key, value) pairs, where value is the last item in
        the list associated with the key.
        """
        return [(key, self[key]) for key in self.keys()]

    def lists(self):
        "Returns a list of (key, list) pairs."
        return dict.items(self)

    def values(self):
        "Returns a list of the last value on every key list."
        return [self[key] for key in self.keys()]

    def copy(self):
        "Returns a copy of this object."
        return self.__deepcopy__()

    def update(self, *args, **kwargs):
        "update() extends rather than replaces existing key lists. Also accepts keyword args."
        if len(args) > 1:
            raise TypeError, "update expected at most 1 arguments, got %d", len(args)
        if args:
            other_dict = args[0]
            if isinstance(other_dict, MultiValueDict):
                for key, value_list in other_dict.lists():
                    self.setlistdefault(key, []).extend(value_list)
            else:
                try:
                    for key, value in other_dict.items():
                        self.setlistdefault(key, []).append(value)
                except TypeError:
                    raise ValueError, "MultiValueDict.update() takes either a MultiValueDict or dictionary"
        for key, value in kwargs.iteritems():
            self.setlistdefault(key, []).append(value)


class QueryDict(MultiValueDict):
    """A specialized MultiValueDict that takes a query string when initialized.
    This is immutable unless you create a copy of it."""
    def __init__(self, query_string, mutable=False):
        MultiValueDict.__init__(self)
        self._mutable = True
        for key, value in parse_qsl((query_string or ''), True): # keep_blank_values=True
            self.appendlist(key, value)
        self._mutable = mutable

    def _assert_mutable(self):
        if not self._mutable:
            raise AttributeError, "This QueryDict instance is immutable"

    def __setitem__(self, key, value):
        self._assert_mutable()
        MultiValueDict.__setitem__(self, key, value)

    def __copy__(self):
        result = self.__class__('', mutable=True)
        for key, value in dict.items(self):
            dict.__setitem__(result, key, value)
        return result

    def __deepcopy__(self, memo={}):
        import copy
        result = self.__class__('', mutable=True)
        memo[id(self)] = result
        for key, value in dict.items(self):
            dict.__setitem__(result, copy.deepcopy(key, memo), copy.deepcopy(value, memo))
        return result

    def setlist(self, key, list_):
        self._assert_mutable()
        MultiValueDict.setlist(self, key, list_)

    def appendlist(self, key, value):
        self._assert_mutable()
        MultiValueDict.appendlist(self, key, value)

    def update(self, other_dict):
        self._assert_mutable()
        MultiValueDict.update(self, other_dict)

    def pop(self, key):
        self._assert_mutable()
        return MultiValueDict.pop(self, key)

    def popitem(self):
        self._assert_mutable()
        return MultiValueDict.popitem(self)

    def clear(self):
        self._assert_mutable()
        MultiValueDict.clear(self)

    def setdefault(self, *args):
        self._assert_mutable()
        return MultiValueDict.setdefault(self, *args)

    def copy(self):
        "Returns a mutable copy of this object."
        return self.__deepcopy__()

    def urlencode(self):
        output = []
        for k, list_ in self.lists():
            output.extend([urlencode({k: v}) for v in list_])
        return '&'.join(output)

class DotDict(object):
	"""
	Dict with dottable items (e.g. t.a => t['a']
	"""
	def __init__(self,items={}):
		self.items = items
	def __getattr__(self, attr):
		try:
			return self[attr]
		except IndexError,e:
			raise AttributeError()
	def __getitem__(self, key):
		if key in self.items:
			return self.items[key]
		else:
			raise IndexError()
	def __setitem__(self,key,value):
		return self.__setattr__(key,value)
	def __len__(self):
		return len(self.items)
	def __contains__(self, key):
		return key in self.items
		
def parse_cookie(cookie):
    if cookie == '':
        return {}
    c = SimpleCookie()
    c.load(cookie)
    cookiedict = {}
    for key in c.keys():
        cookiedict[key] = c.get(key).value
    return cookiedict
    
    
class DebugMsg(Exception):
	def __init__(self, msg):
		Exception.__init__(self)
		self.msg = msg
	def __repr__(self):
		return self.msg
	def __str__(self):
		return self.msg
		

def load_tool(tool_name):
	parts = tool_name.split('.')
	deep = 0
	x = None
	p = None
	if len(parts)>0:
		while deep<len(parts):
			# first try to find the part
			a,b,c = find_module(parts[deep],p)
			# if found, load module
			x = load_module(parts[deep],a,b,c)
			deep += 1
			if deep<len(parts):
				p = x.__path__
			print p
		return x
	else:
		raise ImportError()
