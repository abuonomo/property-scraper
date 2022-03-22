# Automation for reconciliation program
# author: Anthony Buonomo
# email: arb246@georgetown.edu

CHROME_PATH=/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome
CHROMEDRIVER_URL=https://chromedriver.storage.googleapis.com
OS_PATH=chromedriver_mac64.zip


## Download and unzip the chromedriver for your version
update-chromedriver:
	export version_str=$$($(CHROME_PATH) --version); \
	export version_array=($${version_str}); \
	export version=$${version_array[2]}; \
	echo $${version}; \
	export major_version="$$(cut -d'.' -f1 <<<"$${version}")"; \
	echo $${major_version}; \
	export version_url="$$(curl $(CHROMEDRIVER_URL)/LATEST_RELEASE_$${major_version})"; \
	export driver_url=$(CHROMEDRIVER_URL)/$${version_url}/$(OS_PATH); \
	echo $${driver_url}; \
	wget $${driver_url}; \
	unzip chromedriver_mac64.zip; \
	rm chromedriver_mac64.zip; \

INTERPRETER=python
## Get unit codes
codes:
	cd src && python lib.py

## Get transactions for units (run iteratively until complete all)
transactions:
	cd src && python transactions.py

## Combine found data and get most important information
condense:
	cd src && python condense.py

## Run full pipeline
all: codes transactions condense
#################################################################################
# Self Documenting Commands                                                     #
#################################################################################

.DEFAULT_GOAL := help

# Inspired by <http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html>
# sed script explained:
# /^##/:
# 	* save line in hold space
# 	* purge line
# 	* Loop:
# 		* append newline + line to hold space
# 		* go to next line
# 		* if line starts with doc comment, strip comment character off and loop
# 	* remove target prerequisites
# 	* append hold space (+ newline) to line
# 	* replace newline plus comments by `---`
# 	* print line
# Separate expressions are necessary because labels cannot be delimited by
# semicolon; see <http://stackoverflow.com/a/11799865/1968>
.PHONY: help
help:
	@echo "$$(tput bold)Available rules:$$(tput sgr0)"
	@echo
	@sed -n -e "/^## / { \
		h; \
		s/.*//; \
		:doc" \
		-e "H; \
		n; \
		s/^## //; \
		t doc" \
		-e "s/:.*//; \
		G; \
		s/\\n## /---/; \
		s/\\n/ /g; \
		p; \
	}" ${MAKEFILE_LIST} \
	| LC_ALL='C' sort --ignore-case \
	| awk -F '---' \
		-v ncol=$$(tput cols) \
		-v indent=19 \
		-v col_on="$$(tput setaf 6)" \
		-v col_off="$$(tput sgr0)" \
	'{ \
		printf "%s%*s%s ", col_on, -indent, $$1, col_off; \
		n = split($$2, words, " "); \
		line_length = ncol - indent; \
		for (i = 1; i <= n; i++) { \
			line_length -= length(words[i]) + 1; \
			if (line_length <= 0) { \
				line_length = ncol - indent - length(words[i]) - 1; \
				printf "\n%*s ", -indent, " "; \
			} \
			printf "%s ", words[i]; \
		} \
		printf "\n"; \
	}' \
	| more $(shell test $(shell uname) = Darwin && echo '--no-init --raw-control-chars')
