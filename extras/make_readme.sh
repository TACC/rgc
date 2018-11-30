#!/bin/bash

OF=README.md

usage=$(python bin/rgc -h 2>&1 | head -n 1)

python bin/rgc -h 2>&1 | tail -n +3 | sed -e "/positional/i \ 
${usage}
" -e "/positional/i \ 
\ 
" | sed -e "/usage:/i \ 
\`\`\`
" > ${OF}

echo '''```

### Examples

Pulling and generating modules for bwa, samtools, and bowtie

```
rgc -P /data/03076/gzynda/rgc_test -v biocontainers/bwa:0.7.15 biocontainers/samtools:v1.7.0_cv3 biocontainers/bowtie:v1.1.2_cv3
```

API Documentation
------------------------------------------------------''' >> ${OF}

pydocmd simple rgc++ | sed -e "s/^#/##/" -e '/## rgc/d' >> ${OF}
