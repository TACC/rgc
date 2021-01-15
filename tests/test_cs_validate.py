import pytest, logging, os, shutil, tempfile

from rgc.ContainerSystem.validate import validate

def test_registry_exclude():
	v = validate()
	exclude = ['shub://bears','docker://ghcr.io/bears',\
		'docker://docker.pkg.github.com/bears',\
		'docker.pkg.github.com/bears','ghcr.io/bears']
	include = ['shu://bears','docker://bears','quay.io/biocontainers/samtools:1.11--h6270b1f_0','docker://quay.io/biocontainers/samtools:1.11--h6270b1f_0']
	for url in include:
		assert v.registry_exclude_re.match(url) == None
	for url in exclude:
		assert v.registry_exclude_re.match(url) != None

urls = ('gzynda/build-essential:bionic',\
	'gzynda/build-essential',\
	'gzynda/build-essentials:latest',\
	'gzynda/sleepy-server:latest',\
	'shub://bears')
image_tuples = [('dockerhub','gzynda','build-essential'),\
	('dockerhub','gzynda','build-essential'),\
	('dockerhub','gzynda','build-essentials'),\
	('dockerhub','gzynda','sleepy-server'),\
	('shub','library','bears')]
tags_list = [set(['bionic','xenial']),\
	set(['bionic','xenial']),\
	set(),\
	set(['latest']),\
	set()]
valid_list = ('valid', 'invalid', 'invalid', 'valid','invalid')
# Compute valid lists
valid_urls = set([u for u,v in zip(urls,valid_list) if v == 'valid'])
invalid_urls = set([u for u,v in zip(urls,valid_list) if v == 'invalid'])

@pytest.mark.parametrize("url,image_tuple", zip(urls,image_tuples))
def test__getUrlTuple(url, image_tuple):
	v = validate()
	assert v._getUrlTuple(url) == image_tuple

@pytest.mark.parametrize("url,image_tuple,tags", zip(urls,image_tuples,tags_list))
def test__getTags(url, image_tuple, tags):
	v = validate()
	assert v._getTags(url) == tags
	assert v.tag_dict[image_tuple] == tags

def test_validateURL():
	v = validate()
	v.validateURL('shub://bears')
	assert 'shub://bears' in v.invalid
	v.validateURL('docker://biocontainers/bwa:0.7.15')
	assert 'docker://biocontainers/bwa:0.7.15' in v.valid
	v.validateURL('biocontainers/samtools:v1.7.0_cv3')
	assert 'biocontainers/samtools:v1.7.0_cv3' in v.valid

default_dir = os.path.join(os.path.expanduser('~'),'rgc_cache')
def del_cache_dir(p=default_dir):
	if os.path.exists(p):
		shutil.rmtree(p)

def test_validateURLs(caplog):
	caplog.set_level(logging.DEBUG)
	del_cache_dir()
	assert not os.path.exists(default_dir)
	v = validate()
	v.validateURLs(urls)
	assert "Validating all %i URLs"%(len(urls)) in caplog.text
	assert os.path.exists(os.path.join(default_dir,'valid.pkl'))
	assert v.valid == valid_urls
	assert v.invalid == invalid_urls
	# Test restore
	caplog.clear()
	print(v.__dict__)
	del v
	v = validate()
	print(v.__dict__)
	print(v.valid)
	assert os.path.exists(os.path.join(default_dir,'valid.pkl'))
	assert not v.valid
	assert not v.invalid
	v.validateURLs(urls)
	assert v.valid == valid_urls
	assert v.invalid == invalid_urls
	for url in urls:
		assert "Restored %s"%(url) in caplog.text
	del_cache_dir()
