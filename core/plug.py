import re
from apwal.core.utils import DebugMsg

__all__ = [
    'Pluggable',
]

class Pluggable:

    """
    Pluggable application. 

    A pluggable can bind methods to virtual urls (regexp), relatively to 
    its parent. You can build an entire tree of pluggables, by using 
    the @plug([classes]) decorator. Each pluggable added with this decorator
    will register and bind its methods to the top-level pluggable.
    """

    preplugs = []
    route = None

    def __init__(self, route=None, request=None, params={}):
        """
        Initialize our pluggable:
        - generate base url
        - init pluggables
        - map methods
        """
        # if base url defined then clean it
        if route:
            self.route = self.__trim_url(route,first=False)
        else:
            # otherwise no base ('/' by default)
            self.route = ''
        self.params = params
        self.request = request
        self.__pluggables = []
        self.__methods = []
        self.__error_handlers = []
        self.__map_methods()
        self.__load_pluggables()

    def __load_pluggables(self):
        """
        Load pluggables declared with decorator 'plug()'
        """
        if self.preplugs:
            for p in self.preplugs:
                self.plug(p(p.route,self.request,self.params))

    def __trim_url(self, url,first=True):
        """
        Clean url
        """
        if first:
            if len(url)>0:
                if url[0]=='/':
                    url=url[1:]
        if len(url)>0:
            if url[-1]=='/':
                url=url[:-1]
        return url

    def __convert_dynurl(self, url):
        """
        Convert dynurl to partial regexp (withou ^ and $)
        """
        dynparams = re.findall('\{([^:]*):\(([^\)]*)\)\}',url)
        if dynparams:
            for name,regex in dynparams:
                url = url.replace('{%s:(%s)}'%(name,regex),'(?P<%s>%s)'%(name,regex))
        return url

    def getBoundMethods(self):
        """
        Returns currently bound methods and associated urls/regex
        """
        return self.__methods

    def getErrorHandlers(self):
        """
        Returns currently declared error handlers
        """
        for handler in self.__error_handlers:
            yield handler
    
    def plug(self, pluggable):
        """
        Hot plug any pluggable
        """
        # map pluggable bound methods into our module
        for route,method in pluggable.getBoundMethods():
            #print '-> %s' % (self.__url+'/'+self.__trim_url(url))
            self.__methods.append((self.route+'/'+self.__trim_url(route),method))
        
    def __map_methods(self):
        """
        Scan methods and list all bindable methods with their associated
        virtual url (regexp). Regexps are build based on these info.
        """
        self.__methods = []    
        for child in dir(self):
            m = getattr(self,child)
            if 'url' in dir(m) and callable(m):
                if len(self.route)>0:
                    self.__methods.append((self.__convert_dynurl(self.route+'/'+self.__trim_url(m.url)),m))
                else:
                    self.__methods.append((self.__convert_dynurl('/'+self.__trim_url(m.url)),m))
            if hasattr(m, 'onerror') and callable(m):
                for err_code in m.onerror:
                    self.__error_handlers.append((err_code,m))
                
        return self.__methods
    
    def findRoute(self, requestedUrl):
        """
        Check if a pluggable has a route for a given url.
        If so calls the bound method with extra parameters.

        @return    True if a route was found, False otherwise
        """
        urls = ''
        for url,method in self.__methods:
            urls = urls+';'+url
            res = re.match('^%s$'%url,requestedUrl)
            if res:
                if len(res.groupdict())>0:
                    response = method(res.groupdict())
                else:
                    response = method()
                return True,response
        
        return False,None


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
        
class bind:
    """
    Map a method to a given url
    """
    def __init__(self, url):
        self.url = url
    
    def __call__(self, f):
        f.url = self.url
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