import os
import string
import types
import base64

from Cookie import SimpleCookie
from pprint import pformat
from urllib import urlencode, quote
from pywa.core.utils import MultiValueDict,parse_cookie,QueryDict
from pywa.core.settings import Settings

__all__ = [
	'HttpRequest',
	'HttpResponse',
	'parse_file_upload',
	'HttpResponseRedirect',
	'HttpResponsePermanentRedirect',
	'HttpResponseNotModified',
	'HttpResponseNotFound',
	'HttpResponseForbidden',
	'HttpResponseNotAllowed',
	'HttpResponseGone',
	'HttpResponseNeedAuth',
	'JSONResponse',
	'HttpBadAuth',
	'HttpNoAuth',
	'HttpAuthAgent',
]

RESERVED_CHARS="!*'();:@&=+$,/?%#[]"

class Http404(Exception):
    pass

class HttpRequest(object):
    "A basic HTTP request"
    def __init__(self):
        self.GET, self.POST, self.COOKIES, self.META, self.FILES = {}, {}, {}, {}, {}
        self.path = ''
        self.method = None

    def __repr__(self):
        return '<HttpRequest\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s>' % \
            (pformat(self.GET), pformat(self.POST), pformat(self.COOKIES),
            pformat(self.META))

    def __getitem__(self, key):
        for d in (self.POST, self.GET):
            if d.has_key(key):
                return d[key]
        raise KeyError, "%s not found in either POST or GET" % key

    def has_key(self, key):
        return self.GET.has_key(key) or self.POST.has_key(key)

    def get_full_path(self):
        return ''

    def is_secure(self):
        return os.environ.get("HTTPS") == "on"

def parse_file_upload(header_dict, post_data):
    "Returns a tuple of (POST MultiValueDict, FILES MultiValueDict)"
    import email, email.Message
    from cgi import parse_header
    raw_message = '\r\n'.join(['%s:%s' % pair for pair in header_dict.items()])
    raw_message += '\r\n\r\n' + post_data
    msg = email.message_from_string(raw_message)
    POST = MultiValueDict()
    FILES = MultiValueDict()
    for submessage in msg.get_payload():
        if submessage and isinstance(submessage, email.Message.Message):
            name_dict = parse_header(submessage['Content-Disposition'])[1]
            # name_dict is something like {'name': 'file', 'filename': 'test.txt'} for file uploads
            # or {'name': 'blah'} for POST fields
            # We assume all uploaded files have a 'filename' set.
            if name_dict.has_key('filename'):
                assert type([]) != type(submessage.get_payload()), "Nested MIME messages are not supported"
                if not name_dict['filename'].strip():
                    continue
                # IE submits the full path, so trim everything but the basename.
                # (We can't use os.path.basename because it expects Linux paths.)
                filename = name_dict['filename'][name_dict['filename'].rfind("\\")+1:]
                FILES.appendlist(name_dict['name'], {
                    'filename': filename,
                    'content-type': (submessage.has_key('Content-Type') and submessage['Content-Type'] or None),
                    'content': submessage.get_payload(),
                })
            else:
                POST.appendlist(name_dict['name'], submessage.get_payload())
    return POST, FILES

class HttpResponse(object):
    "A basic HTTP response, with content and dictionary-accessed headers"
    def __init__(self, content='', mimetype=None):
        from cat.conf import settings
        self._charset = settings.DEFAULT_CHARSET
        if not mimetype:
            mimetype = "%s; charset=%s" % (settings.DEFAULT_CONTENT_TYPE, settings.DEFAULT_CHARSET)
        if not isinstance(content, basestring) and hasattr(content, '__iter__'):
            self._container = content
            self._is_string = False
        else:
            self._container = [content]
            self._is_string = True
        self.headers = {'Content-Type': mimetype}
        self.cookies = SimpleCookie()
        self.status_code = 200

    def __str__(self):
        "Full HTTP message, including headers"
        return '\n'.join(['%s: %s' % (key, value)
            for key, value in self.headers.items()]) \
            + '\n\n' + self.content

    def __setitem__(self, header, value):
        self.headers[header] = value

    def __delitem__(self, header):
        try:
            del self.headers[header]
        except KeyError:
            pass

    def __getitem__(self, header):
        return self.headers[header]

    def has_header(self, header):
        "Case-insensitive check for a header"
        header = header.lower()
        for key in self.headers.keys():
            if key.lower() == header:
                return True
        return False

    def set_cookie(self, key, value='', max_age=None, expires=None, path='/', domain=None, secure=None):
        self.cookies[key] = value
        for var in ('max_age', 'path', 'domain', 'secure', 'expires'):
            val = locals()[var]
            if val is not None:
                self.cookies[key][var.replace('_', '-')] = val

    def delete_cookie(self, key, path='/', domain=None):
        self.cookies[key] = ''
        if path is not None:
            self.cookies[key]['path'] = path
        if domain is not None:
            self.cookies[key]['domain'] = domain
        self.cookies[key]['expires'] = 0
        self.cookies[key]['max-age'] = 0

    def _get_content(self):
        content = ''.join(self._container)
        if isinstance(content, unicode):
            content = content.encode(self._charset)
        return content

    def _set_content(self, value):
        self._container = [value]
        self._is_string = True

    content = property(_get_content, _set_content)

    def __iter__(self):
        self._iterator = self._container.__iter__()
        return self

    def next(self):
        chunk = self._iterator.next()
        if isinstance(chunk, unicode):
            chunk = chunk.encode(self._charset)
        return chunk

    def close(self):
        if hasattr(self._container, 'close'):
            self._container.close()

    # The remaining methods partially implement the file-like object interface.
    # See http://docs.python.org/lib/bltin-file-objects.html
    def write(self, content):
        if not self._is_string:
            raise Exception, "This %s instance is not writable" % self.__class__
        self._container.append(content)

    def flush(self):
        pass

    def tell(self):
        if not self._is_string:
            raise Exception, "This %s instance cannot tell its position" % self.__class__
        return sum([len(chunk) for chunk in self._container])

class HttpResponseRedirect(HttpResponse):
    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = quote(redirect_to, safe=RESERVED_CHARS)
        self.status_code = 302

class HttpResponsePermanentRedirect(HttpResponse):
    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = quote(redirect_to, safe=RESERVED_CHARS)
        self.status_code = 301

class HttpResponseNotModified(HttpResponse):
    def __init__(self):
        HttpResponse.__init__(self)
        self.status_code = 304

class HttpResponseNotFound(HttpResponse):
    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)
        self.status_code = 404

class HttpResponseForbidden(HttpResponse):
    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)
        self.status_code = 403

class HttpResponseNotAllowed(HttpResponse):
    def __init__(self, permitted_methods):
        HttpResponse.__init__(self)
        self['Allow'] = ', '.join(permitted_methods)
        self.status_code = 405

class HttpResponseGone(HttpResponse):
    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)
        self.status_code = 410

class HttpResponseServerError(HttpResponse):
    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)
        self.status_code = 500

class HttpResponseNeedAuth(HttpResponse):
    def __init__(self,realm='Restricted',type='Basic',msg='Authorization required !'):
	HttpResponse.__init__(self)
	self.status_code = 401
	self.realm = realm
	self.type = type
	self.write(msg)

    def setRealm(self, realm):
    	self.realm = realm
	self.__setHeader()

    def setType(self,type):
    	self.type = type
	self.__setHeader()

    def __setHeader(self):
    	self['WWW-Authenticate']='%s realm="%s"' % (self.type,self.realm)

def get_host(request):
    "Gets the HTTP host from the environment or request headers."
    host = request.META.get('HTTP_X_FORWARDED_HOST', '')
    if not host:
        host = request.META.get('HTTP_HOST', '')
    return host


class JSONResponse(HttpResponse):
    def __init__(self, json):
        HttpResponse.__init__(self,json,'application/json')	
	

class HttpBadAuth:
	def __str__(self):
		return "Authentication failure."
		
class HttpNoAuth:
	def __str__(self):
		return "No Authentication needed"

class HttpAuthAgent:
	
	def __init__(self, auth, realm=""):
		self.realm = realm
		self.__auth = auth
	
	def askCredentials(self,realm=''):
		response = HttpResponseNeedAuth()
		response.setRealm(realm)
		return response

	def Auth(self, req):
		user = None
		pwd = None
		
		if req.META.has_key('Authorization'):
			try:
				header = req.META['Authorization']
				scheme,credentials = header.split(None,1)
				credentials = credentials.strip()
				scheme = scheme.lower()
				if scheme == 'basic':
					credentials = base64.decodestring(credentials)
					user,passwd = string.split(credentials,':',1)
				else:
					raise HttpBadAuth()
			except:
				raise HttpNoAuth()
	
		if self.realm is None:
			raise ModPythonAuthErr()

		if not user:
			return False
		
		if callable(self.__auth):
			return self.__auth(user, passwd)
		elif (type(self.__auth) is types.DictionaryType) and self.__auth.has_key(user):
			if self.__auth[user]==passwd:
				return True
			else:
				return False
		return False


class ModPythonRequest(HttpRequest):
    def __init__(self, req):
        self._req = req
        self.path = req.uri

    def __repr__(self):
        # Since this is called as part of error handling, we need to be very
        # robust against potentially malformed input.
        try:
            get = pformat(self.GET)
        except:
            get = '<could not parse>'
        try:
            post = pformat(self.POST)
        except:
            post = '<could not parse>'
        try:
            cookies = pformat(self.COOKIES)
        except:
            cookies = '<could not parse>'
        try:
            meta = pformat(self.META)
        except:
            meta = '<could not parse>'
        return '<ModPythonRequest\npath:%s,\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s>' % \
            (self.path, get, post, cookies, meta)

    def get_full_path(self):
        return '%s%s' % (self.path, self._req.args and ('?' + self._req.args) or '')

    def is_secure(self):
        # Note: modpython 3.2.10+ has req.is_https(), but we need to support previous versions
        return self._req.subprocess_env.has_key('HTTPS') and self._req.subprocess_env['HTTPS'] == 'on'

    def _load_post_and_files(self):
        "Populates self._post and self._files"
        if self._req.headers_in.has_key('content-type') and self._req.headers_in['content-type'].startswith('multipart'):
            self._post, self._files = parse_file_upload(self._req.headers_in, self.raw_post_data)
        else:
            self._post, self._files = QueryDict(self.raw_post_data), MultiValueDict()

    def _get_request(self):
        if not hasattr(self, '_request'):
            self._request = MergeDict(self.POST, self.GET)
        return self._request

    def _get_get(self):
        if not hasattr(self, '_get'):
            self._get = QueryDict(self._req.args)
        return self._get

    def _set_get(self, get):
        self._get = get

    def _get_post(self):
        if not hasattr(self, '_post'):
            self._load_post_and_files()
        return self._post

    def _set_post(self, post):
        self._post = post

    def _get_cookies(self):
        if not hasattr(self, '_cookies'):
            self._cookies = parse_cookie(self._req.headers_in.get('cookie', ''))
        return self._cookies

    def _set_cookies(self, cookies):
        self._cookies = cookies

    def _get_files(self):
        if not hasattr(self, '_files'):
            self._load_post_and_files()
        return self._files

    def _get_meta(self):
        "Lazy loader that returns self.META dictionary"
        if not hasattr(self, '_meta'):
            self._meta = {
                'AUTH_TYPE':         self._req.ap_auth_type,
                'AUTHORIZATION':     None,#self.auth_data,
				'CONTENT_LENGTH':    self._req.clength, # This may be wrong
                'CONTENT_TYPE':      self._req.content_type, # This may be wrong
                'GATEWAY_INTERFACE': 'CGI/1.1',
                'PATH_INFO':         self._req.path_info,
                'PATH_TRANSLATED':   None, # Not supported
                'QUERY_STRING':      self._req.args,
                'REMOTE_ADDR':       self._req.connection.remote_ip,
                'REMOTE_HOST':       None, # DNS lookups not supported
                'REMOTE_IDENT':      self._req.connection.remote_logname,
                'REMOTE_USER':       self._req.user,
                'REQUEST_METHOD':    self._req.method,
                'SCRIPT_NAME':       None, # Not supported
                'SERVER_NAME':       self._req.server.server_hostname,
                'SERVER_PORT':       self._req.server.port,
                'SERVER_PROTOCOL':   self._req.protocol,
                'SERVER_SOFTWARE':   'mod_python'
            }
            for key, value in self._req.headers_in.items():
                key = 'HTTP_' + key.upper().replace('-', '_')
                self._meta[key] = value
        return self._meta

    def _get_raw_post_data(self):
        try:
            return self._raw_post_data
        except AttributeError:
            self._raw_post_data = self._req.read()
            return self._raw_post_data

    def _get_method(self):
        return self.META['REQUEST_METHOD'].upper()

    GET = property(_get_get, _set_get)
    POST = property(_get_post, _set_post)
    COOKIES = property(_get_cookies, _set_cookies)
    FILES = property(_get_files)
    META = property(_get_meta)
    REQUEST = property(_get_request)
    raw_post_data = property(_get_raw_post_data)
    method = property(_get_method)

class WSGIRequest(HttpRequest):
	"""
	Adapt a mod_wsgi request to an Apache request
	"""
	def __init__(self, environ):
		self._env = environ
		self._req = self._env['wsgi.input']
	
	def document_root(self):
		if 'DOCUMENT_ROOT' in self._env:
			return self._env['DOCUMENT_ROOT']
		else:
			return None

	def __repr__(self):
		# Since this is called as part of error handling, we need to be very
		# robust against potentially malformed input.
		try:
			get = pformat(self.GET)
		except:
			get = '<could not parse>'
		try:
			post = pformat(self.POST)
		except:
			post = '<could not parse>'
		try:
			cookies = pformat(self.COOKIES)
		except:
			cookies = '<could not parse>'
		try:
			meta = pformat(self.META)
		except:
			meta = '<could not parse>'
		return '<WSGIRequest\npath:%s,\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s>' % \
            (self.path, get, post, cookies, meta)

	def get_full_path(self):
		return '%s%s' % (self.path, self._env['QUERY_STRING'] and ('?' + self._env['QUERY_STRING']) or '')

	def is_secure(self):
    	# WSGI defined url_scheme
		return self._env['wsgi.url_scheme'].lower()=='https'

	def _load_post_and_files(self):
		if self._env.has_key('CONTENT_TYPE') and self._env['CONTENT_TYPE'].startswith('multipart'):
			self._post, self._files = parse_file_upload(self._env, self.raw_post_data)
		else:
			self._post, self._files = QueryDict(self.raw_post_data), MultiValueDict()

	def _get_request(self):
		if not hasattr(self, '_request'):
			self._request = MergeDict(self.POST, self.GET)
		return self._request

	def _get_get(self):
		if not hasattr(self, '_get'):
			self._get = QueryDict(self._env['QUERY_STRING'])
		return self._get

	def _set_get(self, get):
		self._get = get

	def _get_post(self):
		if not hasattr(self, '_post'):
			self._load_post_and_files()
		return self._post

	def _set_post(self, post):
		self._post = post

	def _get_cookies(self):
		if not hasattr(self, '_cookies'):
			self._cookies = parse_cookie(self._env.get('HTTP_COOKIE', ''))
		return self._cookies

	def _set_cookies(self, cookies):
		self._cookies = cookies

	def _get_files(self):
		if not hasattr(self, '_files'):
			self._load_post_and_files()
		return self._files

	def _get_meta(self):
		"Lazy loader that returns self.META dictionary"
		if not hasattr(self, '_meta'):
			self._meta = {}
			_metas = [
				'CONTENT_TYPE',
				'CONTENT_LENGTH',
				'PATH_INFO',
				'PATH_TRANSLATED',
				'QUERY_STRING',
				'REQUEST_METHOD',
				'SERVER_NAME',
				'SCRIPT_NAME',
				'SERVER_PORT',
				'SERVER_PROTOCOL',
				'REMOTE_ADDR',
			]
			_headers = [
				'AUTHORIZATION',
				'REMOTE_HOST',
				'REMOTE_IDENT',
				'REMOTE_USER',
			]
			for _meta in _metas:
				if _meta in self._env:
					self._meta[_meta] = self._env[_meta]
			for _header in _headers:
				if 'HTTP_'+_header in self._env:
					self._meta['HTTP_'+_header] = self._env['HTTP_'+_header]
		return self._meta

	def _get_raw_post_data(self):
		try:
			return self._raw_post_data
		except AttributeError:
			self._raw_post_data = self._req.read()
			return self._raw_post_data

	def _get_uri(self):
		return self.META['PATH_INFO']
		
	def _get_hostname(self):
		return self.META['SERVER_NAME']

	def _get_method(self):
		return self.META['REQUEST_METHOD'].upper()

	GET = property(_get_get, _set_get)
	POST = property(_get_post, _set_post)
	COOKIES = property(_get_cookies, _set_cookies)
	FILES = property(_get_files)
	META = property(_get_meta)
	REQUEST = property(_get_request)
	raw_post_data = property(_get_raw_post_data)
	method = property(_get_method)
	uri = property(_get_uri)
	hostname = property(_get_hostname)