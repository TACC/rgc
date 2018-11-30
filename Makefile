docs:
	pydocmd simple rgc++ | sed -e "s/__/**/g" > Documentation.md
