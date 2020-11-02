import pytest, logging
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
