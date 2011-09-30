from core import Pluggable,bind,plug

class Inside(Pluggable):
	def __init__(self):
		Pluggable.__init__(self,'details')
	@bind('get/{id:([0-9]+)}')
	def getDetailsById(self,params):
		return 'Chosen id: %s' % params['id']

@plug(Inside)
class Test2(Pluggable):
	def __init__(self):
		Pluggable.__init__(self,'scope')

	@bind('get')
	def getScopeById(self):
		return 'Called Test2::get'
@plug(Test2)
class Test(Pluggable):
	def __init__(self):
		Pluggable.__init__(self)
	@bind('truc')
	def truc(self,urlparams):
		return 'Called Test::truc'

p = Test()
p.findRoute('/truc')
