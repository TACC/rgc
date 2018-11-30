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

cat << 'EOF' >> ${OF}
```

### Examples

Pulling and generating modules for bwa, samtools, and bowtie

```
rgc biocontainers/bwa:0.7.15 biocontainers/samtools:v1.7.0_cv3 biocontainers/bowtie:v1.1.2_cv3
```

and if you don't have a system running Lmod, feel free to test in docker

```
$ docker run --privileged --rm -it gzynda/rgc:latest bash

$ rgc biocontainers/bwa:0.7.15 biocontainers/samtools:v1.7.0_cv3 biocontainers/bowtie:v1.1.2_cv3
$ module use ${PWD}/modulefiles
$ module avail
$ module load bwa
$ bwa
```

API Documentation
------------------------------------------------------
EOF

pydocmd simple rgc++ | sed -e "s/^#/##/" -e '/## rgc/d' >> ${OF}
