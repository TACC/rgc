import pytest, logging

from rgc.ContainerSystem.url import url_parser
from rgc.helpers import translate, iterdict

urls = ("docker://quay.io/biocontainers/samtools:1.11--h6270b1f_0",\
	"quay.io/biocontainers/samtools:1.11--h6270b1f_0",\
	"shub://user/image:tag",\
	"docker://ghcr.io/user/image",\
	"docker://biocontainers/bwa:0.7.15",\
	"docker://ubuntu:bionic")
san_urls = ("quay.io/biocontainers/samtools:1.11--h6270b1f_0",\
	"quay.io/biocontainers/samtools:1.11--h6270b1f_0",\
	"user/image:tag",\
	"ghcr.io/user/image",\
	"biocontainers/bwa:0.7.15",\
	"ubuntu:bionic")
full_urls = ("https://quay.io/repository/biocontainers/samtools",\
	"https://quay.io/repository/biocontainers/samtools",\
	"https://singularity-hub.org/user/image",\
	"https://ghcr.io/user/image",\
	"https://hub.docker.com/r/biocontainers/bwa",\
	"https://hub.docker.com/r/library/ubuntu")
orgs = ("biocontainers","biocontainers","user","user","biocontainers","library")
names = ("samtools","samtools","image","image","bwa","ubuntu")
tags = ("1.11--h6270b1f_0","1.11--h6270b1f_0","tag",False,"0.7.15","bionic")
registries = ("quay","quay","shub","ghcr","dockerhub","dockerhub")

@pytest.mark.parametrize("url,san_url", zip(urls,san_urls))
def test__sanitize(url, san_url):
	u = url_parser()
	u._sanitize(url)
	assert u.sanitized_url[url] == san_url

@pytest.mark.parametrize("url,san_url", zip(urls,san_urls))
def test_sanitize(url, san_url):
	u = url_parser()
	assert u.sanitize(url) == san_url
	assert u.sanitized_url[url] == san_url

@pytest.mark.parametrize("url,name,tag", zip(urls,names,tags))
def test__split(url, name, tag):
	u = url_parser()
	u._split(url)
	assert u.name[url] == name
	assert u.tag[url] == tag

@pytest.mark.parametrize("url,registry", zip(urls,registries))
def test__detectRegistry(url, registry):
	u = url_parser()
	u._detectRegistry(url)
	assert u.registry[url] == registry

@pytest.mark.parametrize("url,registry", zip(urls,registries))
def test_getRegistry(url, registry):
	u = url_parser()
	assert u.getRegistry(url) == registry
	assert u.registry[url] == registry

@pytest.mark.parametrize("url,full_url", zip(urls,full_urls))
def test__detectRegistry(url, full_url):
	u = url_parser()
	u._fullURL(url)
	assert u.full_url[url] == full_url

@pytest.mark.parametrize("url,san_url,name,tag,registry,full_url", zip(urls,san_urls,names,tags,registries,full_urls))
def test_parseURL(url, san_url, name, tag, registry, full_url):
	u = url_parser()
	u.parseURL(url)
	assert u.sanitized_url[url] == san_url
	assert u.name[url] == name
	assert u.tag[url] == tag
	assert u.registry[url] == registry
	assert u.full_url[url] == full_url
	# Make sure all values except known_registries are reset
	u = url_parser()
	for k,v in iterdict(vars(u)):
		assert not v
	assert u.known_registries
	assert u.full_url_templates
