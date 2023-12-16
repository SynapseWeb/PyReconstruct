#### VARS #################################################################################

# Conda vars
CONDA_BASE = $(shell conda info --base)
CONDA_INIT = source $(CONDA_BASE)/etc/profile.d/conda.sh ; conda activate

# Environment vars
ENV_NAME = pyrecon_dev
ENV_DIR = $(CONDA_BASE)/envs/$(ENV_NAME)
ENV_YAML = environment_dev.yaml

# Other
LINK_SCRIPTS = . ./link_shell.sh $(ENV_DIR)
SHOW_HELP = cat make_help.txt | awk '{gsub("<<<ENV>>>","$(ENV_NAME)",$$0); print $$0}'

#### HELP #################################################################################

.DEFAULT_GOAL := help

.PHONY: help # Generate list of make subcommands with descriptions
help:
	@$(SHOW_HELP)

#### ENVIRONMENT ##########################################################################

.ONESHELL:

.PHONY: env
env:
	conda env create -f $(ENV_YAML) -n $(ENV_NAME)
	$(LINK_SCRIPTS)

.PHONY: update
update:
	conda env update -n $(ENV_NAME) -f $(ENV_YAML) --prune
	$(LINK_SCRIPTS)

.PHONY: clean
clean:
	conda remove --all -n $(ENV_NAME)

.PHONY: remove
remove: clean
