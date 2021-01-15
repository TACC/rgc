from rgc.ContainerSystem.modulefile import modulefile
import os

class ContainerSystem(modulefile):
	def __init__(self, module_dir='./containers', \
			container_dir='./containers', \
			cache_dir=os.path.join(os.path.expanduser('~'),'rgc_cache'), \
			module_system='lmod', force=False, force_cache=False, n_threads=4):
		super(ContainerSystem, self).__init__()
		# modulefile params
		self.moduleDir = module_dir
		self.module_system = module_system
		self.force = force
		# scan parms
		self.force_cache = force_cache
		self.n_threads = n_threads
		# pull params
		self.containerDir = container_dir
		if cache_dir:
			self.cache_dir = cache_dir
			if not os.path.exists(cache_dir): os.makedirs(cache_dir)
		# validate params
		# system params
		self.system = self._detectSystem()
		# cache params
		self.cache_dir = cache_dir
		# metadata params
