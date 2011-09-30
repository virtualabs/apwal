#!/usr/bin/python

import re
import sys
import os
from imp import find_module, load_module

try:
	from mod_python import apache, Session
except ImportError,e:
	pass
from apwal.core.settings import SettingsLoader
from apwal.core.helpers import is_handler
from apwal.http import ModPythonRequest,HttpRequest, HttpResponse, Http404, WSGIRequest
from apwal.core.utils import DebugMsg,load_tool

__all__ = [
	'ApwalDispatcher',
	'handler',
	'WSGIHandler',
]

class ApwalDispatcher:

	def __init__(self, req):
		self.req = req
		self.__wwwroot = self.req.document_root()
		self.vhosts = {}
		self.error_handlers = {}
		self.__read_config(os.path.join(self.__wwwroot,'config.xml'))
		self.__load_pluggables()
	
	def __read_config(self, cfg_file):
		"""
		Load configuration file (generally 'config.xml' at web server's document root
		"""
		self.settings = SettingsLoader(cfg_file).read()
	
	def __load_pluggables(self):
		"""
		Load every loadable pluggables
		"""
		vhosts = self.settings.getVhosts()
		for vhost_name in vhosts:
			# for each vhost, load every pluggable defined in configuration
			self.vhosts[vhost_name] = []
			self.error_handlers[vhost_name] = {}
			for plug in vhosts[vhost_name]:
				# for every plug, try to load it
				try:
					try:
						# try to load plug from web root
						a,b,c=find_module(plug['src'],[self.__wwwroot])
						x=load_module(plug['src'],a,b,c)
					except ImportError,e:
						# if not found, try to load from python defined tools
						# this feature can be useful to load predefined tools
						# included in some packages, such as apwal.tools
						x = load_tool(plug['src'])
					for attr in dir(x):
						# is pluggable a handler ? (decorated with @main)
						if is_handler(getattr(x,attr)):
							try:
								z = getattr(x,attr)(route=plug['route'],request=self.req,params=plug['params'])
								for err_code,method in z.getErrorHandlers():
									self.error_handlers[vhost_name][err_code]=method
								self.vhosts[vhost_name].append(z)
							except TypeError,e:
								raise DebugMsg(plug['src']+'::'+attr+"->%s"%e)
				except ImportError,e:
					# Import error: handle error
					raise DebugMsg('import error: %s'%e)
					# TODO: gestion des erreurs
					pass

					
	def route(self):
		"""
		Route request throughout defined URIs
		"""
		vhost = self.req.hostname
		uri = self.req.uri
		if vhost in self.vhosts:
			for plug in self.vhosts[vhost]:
				status,response = plug.findRoute(uri)
				if status:
					return response
			return None

	def hasErrorHandler(self, error_code):
		"""
		Check if registered pluggables have defined an error handler for the
		given error code
		"""
		vhost = self.req.hostname
		if vhost in self.vhosts:
			return error_code in self.error_handlers[vhost]
		return False
		
	def route_error(self, error_code):
		"""
		Route error through pluggables
		"""
		vhost = self.req.hostname
		uri = self.req.uri
		if vhost in self.vhosts:
			if error_code in self.error_handlers[vhost]:
				return self.error_handlers[vhost][error_code]()
		return None
		
def handler(req):
	_handler = PywaDispatcher(req)
	response = _handler.route()
	if response:
		req.status = 200
		req.content_type = 'text/html'
		req.write(response)
		return apache.OK
	else:
		req.status = 500
		req.write('server error')
		return apache.OK

class WSGIHandler(object):
	def __call__(self, environ, start_response):
		self._handler = ApwalDispatcher(WSGIRequest(environ))
		response = self._handler.route()
		try:
			if response:
				start_response(str(response.status_code)+' WSGI-GENERATED', response.headers.items())
				return [response.content]
			else:
				if self._handler.hasErrorHandler(404):
					response = self._handler.route_error(404)
					start_response(str(response.status_code)+' NOT FOUND', response.headers.items())
					return [response.content]
				else:
					start_response("404 NOT FOUND",[('Content-Type','text/plain')])
					return ['Object not found']
		except Exception,e:
			if self._handler.hasErrorHandler(500):
				response = self._handler.route_error(500)
				start_response(str(response.status_code)+' SERVER ERROR', response.headers.items())
				return [response.content]
			else:
				start_response("500 SERVER ERROR",[('Content-Type','text/plain')])
				return ['Internal server error: %s'%e]
