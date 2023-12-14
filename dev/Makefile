#### HELP #################################################################################

.DEFAULT_GOAL := help

.PHONY: help # Generate list of make subcommands with descriptions
help:

	@echo ""
	echo "To create the development environment run:"
	echo ""
	echo "make env"
	echo ""
	echo "Other possible commands:"
	echo ""
	grep '^.PHONY: .* #' Makefile | sed 's/\.PHONY: \(.*\) # \(.*\)/make \1 : \2/'
	echo ""

#### ENVIRONMENT ##########################################################################

.ONESHELL:

CONDA_BASE = $(shell conda info --base)
CONDA_INIT = source $(CONDA_BASE)/etc/profile.d/conda.sh ; conda activate

ENV_YAML = environment_dev.yaml
ENV_NAME = pyrecon_dev
ENV_BIN = $(CONDA_BASE)/envs/$(ENV_NAME)/bin

SHELL_SCRIPTS = $(shell ls shell)

.PHONY: env # Make a PyReconstruct development environment
env:

	@conda env create -f $(ENV_YAML)

	for script in $(SHELL_SCRIPTS) ; do

		cp shell/$$script $(ENV_BIN)

		chmod +x $(ENV_BIN)/$$script

	done

.PHONY: update # Update the environment
update:

	@conda env update -f $(ENV_YAML) --prune

	for script in $(SHELL_SCRIPTS) ; do

		if [[ -f $(ENV_BIN)/$$script ]]
		then rm $(ENV_BIN)/$$script
		fi

		cp shell/$$script $(ENV_BIN)

		chmod +x $(ENV_BIN)/$$script

	done

.PHONY: clean # Remove the environment completely
clean:

	@$(CONDA_INIT)

	conda remove --all -n $(ENV_NAME)

.PHONY: remove # Alias of 'make clean'
remove: clean
