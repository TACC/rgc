import pytest

from rgc.ContainerSystem.metadata import metadata

urls = ['quay.io/biocontainers/bwa:0.7.3a--hed695b0_5','quay.io/biocontainers/bears:latest']
mds = [{'categories':['Read mapping'],'keywords':['Mapping'],'description':"Fast, accurate, memory-efficient aligner for short and long sequencing reads",'homepage':'http://bio-bwa.sourceforge.net'},\
		{'categories':['Unknown'],'keywords':['Container'],'description':"The bears package",'homepage':False}]

@pytest.mark.parametrize("url,md", zip(urls,mds))
def test__getMetadata(url, md):
	ms = metadata()
	ms._getMetadata(url)
	assert ms.categories[url] == md['categories']
	assert ms.keywords[url] == md['keywords']
	assert ms.description[url] == md['description']
	assert ms.homepage[url] == md['homepage']
