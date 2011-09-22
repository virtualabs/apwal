#!/usr/bin/python

import re
import sys
import os
from imp import find_module, load_module

try:
	from mod_python import apache, Session
except ImportError,e:
	pass
from pywa.core.settings import SettingsLoader
from pywa.core.helpers import is_handler
from pywa.core.http import ModPythonRequest,HttpRequest, HttpResponse, Http404, WSGIRequest
from pywa.core.utils import DebugMsg

__all__ = [
	'PywaDispatcher',
	'handler',
	'WSGIHandler',
]

class PywaDispatcher:

	def __init__(self, req):
		self.req = req
		self.__wwwroot = self.req.document_root()
		self.vhosts = {}
		self.error_handlers = {}
		self.__read_config(os.path.join(self.__wwwroot,'config.xml'))
		self.__load_pluggables()
	
	def __read_config(self, cfg_file):
		self.settings = SettingsLoader(cfg_file).read()
	
	def __load_pluggables(self):
		vhosts = self.settings.getVhosts()
		for vhost_name in vhosts:
			self.vhosts[vhost_name] = []
			self.error_handlers[vhost_name] = {}
			for plug in vhosts[vhost_name]:
				try:
					a,b,c=find_module(plug['src'],[self.__wwwroot])
					x=load_module(plug['src'],a,b,c)
					for attr in dir(x):
						if is_handler(getattr(x,attr)):
							try:
								z = getattr(x,attr)(route=plug['route'],request=self.req,params=plug['params'])
								for err_code,method in z.getErrorHandlers():
									self.error_handlers[vhost_name][err_code]=method
								self.vhosts[vhost_name].append(z)
							except TypeError,e:
								raise DebugMsg(plug['src']+'::'+attr+"->%s"%e)
				except ImportError,e:
					raise DebugMsg('import error: %s'%e)
					# TODO: gestion des erreurs
					pass
			#methods = self.vhosts[vhost_name][1].getBoundMethods()
			#urls = ','.join([url for url,method in methods])
			#raise DebugMsg(urls)

					
	def route(self):
		vhost = self.req.hostname
		uri = self.req.uri
		if vhost in self.vhosts:
			for plug in self.vhosts[vhost]:
				status,response = plug.findRoute(uri)
				if status:
					return response
			return None

	def hasErrorHandler(self, error_code):
		vhost = self.req.hostname
		if vhost in self.vhosts:
			return error_code in self.error_handlers[vhost]
		return False
		
	def route_error(self, error_code):
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
		self._handler = PywaDispatcher(WSGIRequest(environ))
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
		except:
			if self._handler.hasErrorHandler(500):
				response = self._handler.route_error(500)
				start_response(str(response.status_code)+' SERVER ERROR', response.headers.items())
				return [response.content]
			else:
				start_response("500 SERVER ERROR",[('Content-Type','text/plain')])
				return ['Internal server error']