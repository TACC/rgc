import pytest, logging, os, shutil, tempfile
from collections import Counter
from itertools import product
import subprocess as sp
from time import time

from helpers import del_cache_dir, tmp_file
from rgc.helpers import translate, remove_empty_sub_directories

from rgc.ContainerSystem.modulefile import modulefile, curl_tracker_url, validate_tracker_url

def setup_function(function):
	function.cd = tempfile.mkdtemp()
	function.ms = modulefile()
	function.ms.cache_dir = function.cd
	function.ms.moduleDir = tempfile.mkdtemp()
	function.ms.containerDir = tempfile.mkdtemp()

def teardown_function(function):
	del_cache_dir(function.cd)
	del_cache_dir(function.ms.containerDir)
	del_cache_dir(function.ms.moduleDir)
	del function.cd
	del function.ms

tracker_urls = [\
	'https://docs.google.com/forms/d/e/1FAIpQLSdLcvekCL9ads0MvfoY2hLKWgCU_ck1RbDrmKYymaJpY5WWsA/viewform?usp=pp_url&entry.288148883=$%7B%7BSLURM_JOB_ID%7D%7D&entry.104394543=$%7B%7BTACC_SYSTEM%7D%7D&entry.264814955=package_name&entry.750252445=package_version&entry.2023109786=application', \
	'https://docs.google.com/forms/d/e/1FAIpQLSdLcvekCL9ads0MvfoY2hLKWgCU_ck1RbDrmKYymaJpY5WWsA/viewform?usp=pp_url&entry.288148883=$%7BSLURM_JOB_ID%7D&entry.104394543=$%7BTACC_SYSTEM%7D&entry.264814955=package_name&entry.750252445=package_version&entry.2023109786=application', \
	'https://docs.google.com/forms/d/e/1FAIpQLSdLcvekCL9ads0MvfoY2hLKWgCU_ck1RbDrmKYymaJpY5WWsA/viewform?usp=pp_url&entry.288148883=$%7B%7BSLURM_JOB_ID%7D%7D&entry.104394543=$%7B%7BTACC_SYSTEM%7D%7D&entry.264814955=package_name&entry.750252445=package_version&entry.2023109786=bad_application',\
	'https://docs.google.com/forms/d/e/1FAIpQLSdLcvekCL9ads0MvfoY2hLKWgCU_ck1RbDrmKYymaJpY5WWsA/viewform?usp=pp_url&entry.288148883=$%7B%7BSLURM_JOB_ID%7D%7D&entry.104394543=$%7B%7BTACC_SYSTEM%7D%7D&entry.264814955=package_name&entry.750252445=package_version&entry.2023109786=missing']
#curl -sL %sformResponse -d submit=Submit%s &>/dev/null
curl_urls = [\
	'curl -sL https://docs.google.com/forms/d/e/1FAIpQLSdLcvekCL9ads0MvfoY2hLKWgCU_ck1RbDrmKYymaJpY5WWsA/formResponse -d submit=Submit -d entry.288148883=${{SLURM_JOB_ID}} -d entry.104394543=${{TACC_SYSTEM}} -d entry.264814955={package_name} -d entry.750252445={package_version} -d entry.2023109786={application} &>/dev/null', \
	'curl -sL https://docs.google.com/forms/d/e/1FAIpQLSdLcvekCL9ads0MvfoY2hLKWgCU_ck1RbDrmKYymaJpY5WWsA/formResponse -d submit=Submit -d entry.288148883=${{SLURM_JOB_ID}} -d entry.104394543=${{TACC_SYSTEM}} -d entry.264814955={package_name} -d entry.750252445={package_version} -d entry.2023109786={application} &>/dev/null', \
	'', '']
valid_list = [1,1,0,0]
missing_list = [set(),set(),{'application',},{'application',}]

baseline = ['biocontainers/biocontainers:v1.2.0_cv1', 'biocontainers/biocontainers:vdebian-buster-backports_cv1', 'biocontainers/biocontainers:v1.1.0_cv2','biocontainers/biocontainers:v1.0.0_cv4','biocontainers/biocontainers:v1.0.0_alpine_cv1']

urls = ['quay.io/biocontainers/bwa:0.7.3a--hed695b0_5','quay.io/centos/centos:centos7']
contacts = ['one,two','']
mod_prefix_list = ['ctr','']
pathPrefix_list = ['$PP', '']
turls = [tracker_urls[0],'']
force = [False, True]

def test_genModFiles(caplog):
	ms = test_genModFiles.ms
	ms.pullAll(urls)
	ms.scanAll()
	ms.genModFiles()
	for url in urls:
		name, tag = ms.name[url], ms.tag[url]
		mFile = os.path.join(ms.moduleDir, name, "%s.lua"%(tag))
		assert os.path.exists(mFile)

@pytest.mark.parametrize("url,pathPrefix,contact_url,mod_prefix,tracker_url,force", list(product(urls, pathPrefix_list, contacts, mod_prefix_list, turls, force)))
def test_genLMOD(url, pathPrefix, contact_url, mod_prefix, tracker_url, force, caplog):
	ms = test_genLMOD.ms
	ms.genLMOD(url, pathPrefix, contact_url, mod_prefix, tracker_url, force)
	name, tag = ms.name[url], ms.tag[url]
	module_tag = '%s-%s'%(mod_prefix, tag) if mod_prefix else tag
	mFile = os.path.join(ms.moduleDir, name, "%s.lua"%(module_tag))
	assert os.path.exists(mFile)
	with open(mFile,'r') as MF:
		mText = MF.read()
	if 'bwa' in url:
		assert 'bwa' in mText
	else:
		assert 'bwa' not in mText
	for url in contact_url.split(','):
		assert url in mText
	assert module_tag in mText
	if tracker_url: assert 'curl ' in mText
	else: assert 'curl ' not in mText
	if pathPrefix and ms.system != 'docker': assert pathPrefix in mText

@pytest.mark.parametrize("url,valid,missing", zip(tracker_urls,valid_list,missing_list))
def test_validate_tracker_url(url, valid, missing, caplog):
	if valid:
		assert url == validate_tracker_url(url)
	else:
		with pytest.raises(ValueError):
			validate_tracker_url(url)
			missing_msg = "Missing {%s}"%(', '.join(sorted(list(missing))))
			assert missing_msg in caplog.text

@pytest.mark.parametrize("url,curl,valid,missing", zip(tracker_urls,curl_urls,valid_list,missing_list))
def test_curl_tracker_url(url, curl, valid, missing, caplog):
	if not valid: return True
	ret = curl_tracker_url(url)
	assert ret == curl

def test_curl_tracker_url_same():
	p0 = curl_tracker_url(tracker_urls[0])
	p1 = curl_tracker_url(tracker_urls[1])
	assert p0 == p1
	for purl in (p0,p1):
		assert '${{SLURM_JOB_ID}}' in purl
		assert '{application}' in purl
