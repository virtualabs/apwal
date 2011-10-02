#-*- coding:utf-8 -*-
import os,mimetypes
from apwal import *

from apwal.http import HttpResponse,HttpPlainText

__all__ = [
	'DirListing',
]

@main
class DirListing(Pluggable):

	def _get_parent(self, directory):
		r = '/'.join(directory.split('/')[:-2])
		if r=='/':
			return ''
		else:
			return r
	
	def list_dir(self,root,directory):
		output = '<html><head><title>Index of %s</title></head><body>' % ('/'+directory)
		output += '<h2>Index of %s</h2><hr/>' % ('/'+directory)
		output += '<a href="%s"><b>[+] Parent directory</b></a><br/>' % (self.route+'/'+self._get_parent(directory))
		try:
			# list files and directories
			if directory == '/':
				directory = ''
			root = os.path.join(root,directory)
			items = os.listdir(unicode(root))
			dirs = []
			files = []
			for i in items:
				if os.path.isdir(os.path.join(root,i)):
					dirs.append(i)
				if os.path.isfile(os.path.join(root,i)):
					files.append(i)
			dirs.sort()
			files.sort()
			# generate output
			for d in dirs:
				_d = os.path.join(unicode(directory),unicode(d))
				output+= '<a href="%s/"><b>[+]</b> %s</a><br/>' % (d,d)
			for f in files:
				_f = os.path.join(unicode(directory),unicode(f))
				output += '<a href="%s">%s</a><br/>' % (f,f)
			output += '</body></html>'
		except IOError,e:
			output += "<b>Cannot access file or directory</b><br/></body></html>"
		except OSError,e:
			output += "<b>Cannot access file or directory</b><br/></body></html>"
		return output

	@bind('/{target:([0-9a-zA-Z\.\-\_\/]+)}?')
	def list_or_read_file(self, urlparams=None):
		# is target a file ?
		if os.path.isfile(os.path.join(self.params['root'],urlparams['target'])):
			try:
				fpath = os.path.join(self.params['root'],urlparams['target'])
				mt,extension = mimetypes.guess_type(fpath)
				return HttpResponse(open(fpath, 'r').read(),mt)
			except OSError,e:
				return HttpResponse('Cannot read file !')
			except IOError,e:
				return HttpResponse('Not able to read file content !')
		else:
			return HttpResponse(self.list_dir(self.params['root'],urlparams['target']))
	
	@bind('/')
	def list_directory(self, urlparams=None):
		return HttpResponse(self.list_dir(self.params['root'],''))
