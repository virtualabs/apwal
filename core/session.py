import os, time, datetime, random, base64, uuid, re
from apwal.core.utils import ThreadDict
from apwal.core.settings import Settings

## Imports

try:
    import cPickle as pickle
except ImportError:
    import pickle

class SessionExpired(Exception):
	def __init__(self, session):
		Exception.__init__(self)
		self.session = session
	def __repr__(self):
		return '<SessionExpired timeout=%s>' % self.session.getTimeout()

class Session:
	"""
	Web session
	"""
	def __init__(self,store=None, session_uuid=None):
		if session_uuid:
			self.uuid = session_uuid
		else:
			self.uuid = uuid.uuid1()
		self.timeout = int(time.time())+24*3600*1000
		self.content = {}
		if store:
			self.store = store
		else:
			self.store = Settings.globals.sessions_store()
		
	def toArray(self):
		return {'uuid':self.uuid,'timeout':self.timeout,'content':self.content}
	
	@staticmethod
	def fromArray(array, store):
		session = Session(store, array['uuid'])
		session.timeout = array['timeout']
		session.content = array['content']
		return session
	
	@staticmethod
	def fromStore(session_uuid,store=None):
		if store:
			return store.load(session_uuid)
		else:
			store = Settings.globals.sessions_store()
			return store.load(session_uuid)	
	
	def __getitem__(self, key):
		return self.content[key]
		
	def __setitem__(self, key, value):
		self.content[key] = value
		
	def __len__(self):
		return len(self.content)
		
	def isExpired(self):
		return self.timeout<=int(time.time())
		
	def save(self):
		self.store.save(self)


class SessionStoreMustImplement(Exception):
	def __init__(self, method):
		self._method = method
	def __repr__(self):
		return 'SessionStore child class must implement %s' % self._method
	def __str__(self):
		return self.__repr__()

class SessionStore(object):
	"""
	Session store template
	"""
	def __init__(self):
		return
		
	def cleanup(self):
		raise SessionStoreMustImplement('cleanup')
		
	def save(self, session):
		raise SessionStoreMustImplement('save')
		
	def load(self, id):
		raise SessionStoreMustImplement('load')
		
	def __contains__(self, id):
		raise SessionStoreMustImplement('__contains__')

class FileSystemStore(SessionStore):
	"""
	Default session store
	"""
	
	def __init__(self, sessions_root=None):
		if sessions_root:
			self._root = sessions_root
		else:
			self._root = Settings.globals.sessions_root
		return
		
	def cleanup(self):
		# load all sessions and clean expired sessions
		sessions = os.listdir(self._root)
		for session in sessions:
			session_file = os.path.join(self._root,session)
			if re.match('^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', session):
				session = Session.fromArray(pickle.load(open(session_file,'r')), self)
				if session.isExpired():
					os.remove(session_file)
		
	def __contains__(self, uuid):
		"""
		Check if a session is present or not
		"""
		self.cleanup()
		sessions = os.listdir(self._root)
		return session_id in sessions
		
	def save(self, session):
		"""
		Save session
		"""
		session_file = os.path.join(self._root,str(session.uuid))
		session_handle = open(session_file,'w')
		pickle.dump(session.toArray(), session_handle)
		session_handle.close()
		
	def load(self, uuid):
		"""
		Load session
		"""
		# load all sessions and clean expired sessions
		self.cleanup()
		sessions = os.listdir(self._root)
		if uuid in sessions:
			session_file = os.path.join(self._root,uuid)
			session_handle = open(session_file,'r')
			s = Session.fromArray(pickle.load(session_handle), self)
			session_handle.close()
			return s

if __name__=='__main__':
	# gobal settings
	Settings.globals['sessions_root'] = '/tmp/'
	Settings.globals['sessions_store'] = FileSystemStore
	# my session
	my_session = Session()
	my_session['Username']='Goofy'
	my_session.save()
	# reload session
	session2 = Session.fromStore(str(my_session.uuid))
	print 'Username: %s' % session2['Username']
