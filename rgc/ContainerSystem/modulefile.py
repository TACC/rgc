import sys, os, logging, json, re
import subprocess as sp
logger = logging.getLogger(__name__)

from rgc.ContainerSystem.scan import scan
from rgc.helpers import translate, iterdict, retry_call, delete, unescapeURL

class modulefile(scan):
	module_systems = {'lmod'}
	template_files = {system:os.path.join(os.path.dirname(__file__), 'templates/%s.tmpl'%(system)) for system in module_systems}
	def __init__(self, module_dir='./containers', module_system='lmod'):
		super(modulefile, self).__init__()
		self.moduleDir = module_dir
		self.module_system = module_system
		self.template_text = {}
		for ms, tf in iterdict(self.template_files):
			with open(tf) as IF: self.template_text[ms] = IF.read()
	def genModFiles(self, pathPrefix='', contact_url='', mod_prefix='', delete_old=False, tracker_url='', force=False, lmod_prereqs=[]):
		'''
		Generates an Lmod modulefile for every valid image

		# Parameters
		url (str): Image url used to pull
		pathPrefix (str): Prefix to prepend to containerDir (think environment variables)
		contact_url (list): List of contact urls for reporting issues
		mod_prefix (str): Container module files can be tagged with mod_prefix-tag for easy stratification from native modules
		delete_old (bool): Delete outdated module files
		'''
		logger.info("Creating Lmod files for specified all %i images"%(len(self.images)))
		for url in self.images:
			if self.module_system == 'lmod':
				self.genLMOD(url, pathPrefix, contact_url, mod_prefix, tracker_url, force, lmod_prereqs)
			else:
				logger.error("The %s module system is not currently supported"%(self.module_system))
		if delete_old:
			# Generate all module names
			recent_modules = set([])
			for url in self.images:
				name, tag = self.name[url], self.tag[url]
				module_tag = '%s-%s'%(mod_prefix, tag) if mod_prefix else tag
				module_file = os.path.join(self.moduleDir, name, '%s.lua'%(module_tag))
				recent_modules.add(module_file)
			# Delete extras
			self.logger.info("Deleting unused module files")
			all_files = set((os.path.join(p, f) for p, ds, fs in os.walk(self.moduleDir) for f in fs))
			to_delete = all_files - recent_modules
			for fpath in to_delete:
				if fpath.split('.')[-1] == 'lua':
					logger.info("Deleting old modulefile %s"%(fpath))
					os.remove(fpath)
	def genLMOD(self, url, pathPrefix, contact_url, mod_prefix='', tracker_url='', force=False, lmod_prereqs=[]):
		'''
		Generates an Lmod modulefile based on the cached container.

		example link:

		>>> from rgc.helpers import unescapeURL
		>>> unescapeURL('https://docs.google.com/forms/d/e/1FAIpQLSdLcvekCL9ads0MvfoY2hLKWgCU_ck1RbDrmKYymaJpY5WWsA/viewform?usp=pp_url&entry.288148883=$%7B%7BSLURM_JOB_ID%7D%7D&entry.104394543=$%7B%7BTACC_SYSTEM%7D%7D&entry.264814955=%7Bpackage_name%7D&entry.750252445=%7Bpackage_version%7D&entry.2023109786=%7Bapplication%7D')
			'https://docs.google.com/forms/d/e/1FAIpQLSdLcvekCL9ads0MvfoY2hLKWgCU_ck1RbDrmKYymaJpY5WWsA/viewform?usp=pp_url&entry.288148883=${{SLURM_JOB_ID}}&entry.104394543=${{TACC_SYSTEM}}&entry.264814955={package_name}&entry.750252445={package_version}&entry.2023109786={application}'

		# Parameters
		url (str): Image url used to pull
		pathPrefix (str): Prefix to prepend to containerDir (think environment variables)
		contact_url (list): List of contact urls for reporting issues
		mod_prefix (str): Container module files can be identified with mod_prefix-tag for easy stratification from native modules
		'''
		if url in self.invalid: return False
		if url not in self.programs: self.scanPrograms(url)
		#####
		name, tag = self.name[url], self.tag[url]
		module_tag = '%s-%s'%(mod_prefix, tag) if mod_prefix else tag
		keywords = ', '.join(self.keywords[url])
		categories = ', '.join(self.categories[url])
		sorted_progs = sorted(self.getPrograms(url))
		progList = '"'+'", "'.join(sorted_progs)+'"'
		progStr = ' - '+'\n - '.join(sorted_progs)
		img_path = self.images[url].lstrip('./')
		contacts = '\t'+'\n\t'.join(contact_url.split(','))
		#####
		mPath = os.path.join(self.moduleDir, name)
		outFile = os.path.join(mPath, "%s.lua"%(module_tag))
		if os.path.exists(outFile) and not force:
			logger.debug("%s already exists. Skipping"%(outFile))
			return True
		#####
		# Make sure there are programs to expose
		assert progList
		# Populate template
		cmd_str = self._gen_function_prefix(url, pathPrefix, module_tag, tracker_url)
		# make shell functions
		#func_str = '\n'.join(('set_shell_function("{program}", "RGC_APP={program}; " .. run_function .. " $@", "RGC_APP={program}; " .. run_function .. " $*")'.format(program=prog) for prog in sorted_progs))
		template_text = self.template_text['lmod']
		full_text = template_text.format(categories=categories, contact=contacts, \
			decription=self.description[url], home_url=self.homepage[url], \
			keywords=keywords, name=name, run_function=cmd_str, \
			programs_list=progList, programs_string=progStr, \
			url=self.sanitized_url[url], version=module_tag, \
			web_url=self.full_url[url]) #, shell_functions=func_str)
		# add prereqs
		if lmod_prereqs and lmod_prereqs[0]:
			prereq_string = '","'.join(lmod_prereqs)
			full_text += '\ndepends_on("%s")\n'%(prereq_string)
			full_text += 'prereq("%s")\n'%(prereq_string)
		#####
		if not os.path.exists(mPath): os.makedirs(mPath)
		with open(outFile,'w') as OF: OF.write(full_text)
		return True
	def _gen_function_prefix(self, url, pathPrefix, module_tag, tracker_url=""):
		'''
		Looks for {package_name}, {package_version}, and {application} in the tracker_url
		'''
		name, tag = self.name[url], self.tag[url]
		img_path = self.images[url].lstrip('./')
		if 'singularity' in self.system:
			prefix_path = os.getcwd()
			if pathPrefix:
				logger.debug("Using %s as a path prefix"%(pathPrefix))
				prefix_path = pathPrefix
			prefix = 'singularity exec %s $RGC_APP'%(os.path.join(prefix_path, img_path))
		elif self.system == 'docker':
			prefix = 'docker run --rm -it %s $RGC_APP'%(img_path)
		else:
			logger.error("Unhandled system")
			raise ValueError
		if tracker_url:
			curl_cmd = curl_tracker_url(tracker_url).format(package_name=name, \
				package_version=module_tag, \
				application="$RGC_APP")
			prefix = '%s; %s'%(curl_cmd, prefix)
		return prefix

# Tracker URL generation functions
tracker_targets = {'package_name', 'package_version', 'application'}
field_re = re.compile(r'(?<=\&)(entry.\d+)=([^&]+)')
def validate_tracker_url(url):
	ue_url = unescapeURL(url)
	found_targets = set()
	for m in field_re.finditer(ue_url):
		field = m.group(2)
		if field in tracker_targets: found_targets.add(field)
	missing_targets = sorted(list(tracker_targets - found_targets))
	if missing_targets:
		logger.error("Missing {%s} field[s] in tracker url:\n\t%s"%(', '.join(missing_targets), ue_url))
		raise ValueError
	return url
def curl_tracker_url(url):
	ue_url = unescapeURL(url)
	bu_re = re.compile(r'https://docs.google.com/forms/././\w+/(?=viewform)')
	base_url = bu_re.match(ue_url).group(0)
	data_str = ''
	for m in field_re.finditer(ue_url):
		sanitized = re.sub(r'\$\{(\w+)\}', r'${{\1}}', m.group(2))
		sanitized = re.sub(r'^(%s)$'%('|'.join(tracker_targets)), r'{\1}', sanitized)
		data_str += ' -d %s=%s'%(m.group(1), sanitized)
	return 'curl -sL %sformResponse -d submit=Submit%s &>/dev/null'%(base_url, data_str)
