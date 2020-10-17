import sys, os, logging
logger = logging.getLogger(__name__)
import subprocess as sp

from rgc.helpers import translate

class system:
	def __init__(self):
		super(system, self).__init__()
		self.system = None

	def _detectSystem(self, target=''):
		'''
		Looks for container systems in the following order

		 1. docker
		 2. singularity

		container systems installed and running on
		the host.

		# Raises
		SystemError: If neither docker nor singularity is found

		# Returns
		str: conainter system
		'''
		if target:
			if target == 'docker' and self._detectDocker():
				return 'docker'
			elif target == 'singularity' and self._detectSingularity():
				return self._detectSingularity()
			else:
				logger.error("Unsupported target container system: %s"%(target))
				raise ValueError
		# Check for docker
		dd = self._detectDocker()
		if dd: return dd
		# Check for singularity
		ds = self._detectSingularity()
		if ds: return ds
		# No container system detected
		self.logger.error("No supported container system detected on system")
		raise SystemError
	def _detectDocker(self):
		if not sp.call('docker info &>/dev/null', shell=True):
			logger.debug("Detected docker for container management")
			return 'docker'
		return False
	def _detectSingularity(self):
		if not sp.call('singularity help &>/dev/null', shell=True):
			logger.debug("Detected singularity for container management")
			#singularity version 3.3.0-1.fc29
			#2.6.0-dist
			sing_version = translate(sp.check_output('singularity --version', shell=True)).rstrip('\n').split()
			if len(sing_version) > 1:
				sing_version = sing_version[2]
			else:
				sing_version = sing_version[0]
			split_version = sing_version.split('.')
			version = split_version[0]
			self.point_version = split_version[1]
			logger.debug("Detected singularity %c.%c"%(split_version[0], split_version[1]))
			return 'singularity%c'%(version)
		return False
