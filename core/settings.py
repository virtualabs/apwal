from xml.dom.minidom import parse
from apwal.core.utils import DebugMsg,DotDict

class Settings:
	"""
	Settings object
	"""


	globals = DotDict({
		'sessions_mod':None,
		'sessions_root':'/tmp/',
		'sessions_timeout':24*3600*1000,
		'default_charset':'utf-8',
		'default_mime':'text/html',
	})

	def __init__(self):
		self.vhosts = {}
		self.session_store = None
		self.session_cookie = 'pywaid'
		self.session_ipchange = False
		
	def set_vhost(self, vhost_name, plugs):
		self.vhosts[vhost_name] = plugs
		
	def set_session(self, store, ipchange=False, cookiename='pywaid'):
		self.session_store = store
		self.session_cookie = cookiename
		self.session_ipchange = ipchange
		
	def trackSessionIP(self):
		return self.session_ipchange
		
	def getStoreName(self):
		return self.session_store
		
	def getCookieName(self):
		return self.session_cookie
		
	def getVhosts(self):
		return self.vhosts

class SettingsLoader:
	
	"""
	Config file loader
	"""
	
	def __init__(self, cfg_file):
		self.cfg_file = cfg_file
		self.settings = Settings()
		
	def read(self):
		"""
		Read configuration file, parse it and load it into a configuration object
		"""
		self.__cfg = parse(self.cfg_file)
		
		# get session parameters if present
		sessions = self.__cfg.getElementsByTagName('sessions')
		if len(sessions)>=1:
			session = sessions[0]
			Settings.globals['sessions_mode'] = session.getAttribute('type')
			Settings.globals['sessions_root'] = session.getAttribute('path')
			Settings.globals['sessions_timeout'] = session.getAttribute('timeout')
		
		# get all the vhosts
		vhosts = self.__cfg.getElementsByTagName('vhost')
		for vhost in vhosts:
			# get vhost config
			vhost_name = vhost.getAttribute('name')
			if vhost_name:
				# get vhost plugs and associated routes
				vhost_plugs = []
				vhost_tools = []
				plugs = vhost.getElementsByTagName('plug')
				for plug in plugs:
					plug_src = plug.getAttribute('src')
					plug_route = plug.getAttribute('route')
					params = plug.getElementsByTagName('param')
					plug_params = {}
					for param in params:
						param_name = param.getAttribute('name')
						param_value = param.getAttribute('value')
						plug_params[param_name] = param_value
					vhost_plugs.append({'src':plug_src, 'route':plug_route,'params':plug_params})
				self.settings.set_vhost(vhost_name, vhost_plugs)
		
		# return current settings		
		return self.settings

if __name__ == '__main__':
	settings_loader = SettingsLoader('/var/www/apwal-test/config.xml')
		
