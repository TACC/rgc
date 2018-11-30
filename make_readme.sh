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

API Documentation
------------------------------------------------------''' >> ${OF}

pydocmd simple rgc++ | sed -e "s/^#/##/" -e '/## rgc/d' >> ${OF}
