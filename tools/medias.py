import os
import mimetypes
from apwal import *
from apwal.http import HttpResponse,HttpResponseForbidden,HttpResponseNotFound

@main
class MediaServer(Pluggable):
	
	@bind('/{media:([0-9a-zA-Z\.\-\_\/]+)}')
	def serve_media(self, urlparams):
		# look for allowed extensions
		if 'allow' in self.params:
			exts = self.params['allow'].upper().split(',')
		else:
			exts = None		
		if 'directory' in self.params:
			media_dir = self.params['directory']
			required_media = urlparams['media']
			f = os.path.join(media_dir,required_media)
			if os.path.isfile(f):
				mt,encoding = mimetypes.guess_type(f) 
				if exts:
					# get ext
					name,ext = os.path.splitext(required_media.upper())
					if ext[1:] in exts:
						return HttpResponse(open(f,'rb').read(),mt)
					else:
						return HttpResponseNotFound()
				else:
					return HttpResponse(open(f,'rb').read(),mt)
			else:
				return HttpResponseNotFound()
		else:
			return HttpResponseNotFound()