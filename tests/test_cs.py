import pytest, logging, os, shutil, tempfile
from itertools import product
import subprocess as sp
from time import time

from helpers import del_cache_dir, tmp_file
from rgc.ContainerSystem import ContainerSystem

def setup_function(function):
	function.cd = tempfile.mkdtemp()
	function.cs = ContainerSystem()
	function.cs.cache_dir = function.cd
	function.cs.moduleDir = tempfile.mkdtemp()
	function.cs.containerDir = tempfile.mkdtemp()

def teardown_function(function):
	del_cache_dir(function.cd)
	del_cache_dir(function.cs.containerDir)
	del_cache_dir(function.cs.moduleDir)
	del function.cd
	del function.cs

url_list = ['quay.io/biocontainers/bwa:0.7.3a--hed695b0_5',\
	'quay.io/biocontainers/bears:latest',\
	'quay.io/centos/centos:centos7',\
	'quay.io/biocontainers/samtools:1.11--h6270b1f_0']
valid_list = [1,0,1,1]

def test_api(caplog):
	cs = test_api.cs
	# Validate
	cs.validateURLs(url_list)
	assert os.path.exists(os.path.join(cs.cache_dir, 'valid.pkl'))
	for url, valid in zip(url_list, valid_list):
		if valid:
			assert "%s is valid"%(url) in caplog.text
		else:
			assert '%s is an invalid URL'%(url) in caplog.text
	caplog.clear()
	# Pull
	cs.pullAll(url_list)
	assert os.path.exists(os.path.join(cs.cache_dir, 'metadata.pkl'))
	for url, valid in zip(url_list, valid_list):
		if valid:
			assert url in cs.images
		else:
			assert "Not pulling. %s is an invalid URL"%(url) in caplog.text
			assert url not in cs.images
	caplog.clear()
	# Scan
	cs.scanAll()
	assert os.path.exists(os.path.join(cs.cache_dir, 'programs.pkl'))
	for url, valid in zip(url_list, valid_list):
		if valid:
			assert url in cs.programs
		else:
			assert url not in cs.programs
	caplog.clear()
	# Generate modulefiles
	cs.genModFiles()
	for url, valid in zip(url_list, valid_list):
		name, tag = cs.name[url], cs.tag[url]
		mFile = os.path.join(cs.moduleDir, name, "%s.lua"%(tag))
		if valid:
			assert os.path.exists(mFile)
		else:
			assert not os.path.exists(mFile)
