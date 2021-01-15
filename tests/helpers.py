import pytest, logging, os, shutil, tempfile
logger = logging.getLogger(__name__)

class mock:
	def __init__(self, dict_vals):
		self.dict_vals = dict_vals
	def choose(self, *args, **kwargs):
		try:
			logger.debug("Returning %s: %s"%(str(args[0]), self.dict_vals[args[0]]))
			return self.dict_vals[args[0]]
		except:
			logger.debug("Returning default: "+str(kwargs['default']))
			return kwargs['default']
	def true(self, *args, **kwargs):
		return self.choose(default=True, *args, **kwargs)
	def false(self, *args, **kwargs):
		return self.choose(default=False, *args, **kwargs)

def del_cache_dir(p):
	if os.path.exists(p):
		shutil.rmtree(p)

def tmp_file(split=False):
	tmp_file = tempfile.mkstemp()[1]
	os.remove(tmp_file)
	if split:
		return tmp_file, *os.path.split(tmp_file)
	return tmp_file
