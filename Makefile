#!/bin/bash

# Setting
.DEFAULT_GOAL := info
SHELL := /bin/bash

info:
	@echo ""
	@echo -e "----------------------------------------------------------------------"
	@echo -e "\t\t\t|   \e[34m$(shell yq ".name" project.yaml)\e[0m   |"
	@echo -e "----------------------------------------------------------------------"
	@echo -e ""
	@echo -e "~> Version: $(shell yq ".version" project.yaml)"
	@echo -e "~> Description: $(shell yq ".description" project.yaml)"
	@echo -e "~> Revision: $(shell yq ".revision" project.yaml)"
	@echo -e ""
	@echo -e ""

info-release:
	@gh release list --exclude-drafts --exclude-pre-releases --repo "thuyetbao/snapfire"

info-release-latest:
	@gh release list --exclude-drafts --exclude-pre-releases --repo "thuyetbao/snapfire" --limit 1


# ==============================================================================
# (Development) Local ==========================================================
# ==============================================================================

.PHONY: venv

venv:
	@uv venv --allow-existing --color "auto" --python 3.12.10 --seed venv

install-dev:
	@uv pip install "pip>=24.3.1,<=25.0.10" "setuptools>=75.8.0,<78.0.0" "wheel>=0.45.1,<=0.45.10" "wheel>=0.45.1,<0.50.0" "hatch>=1.12.1,<1.15.0" "setuptools<80.0.0" --no-cache
	@uv pip install -r requirements-dev.txt --no-cache



install-application:
	@uv pip install \
		-r application/requirements.txt \
		-r application/requirements-document.txt \
		-r application/requirements-dev.txt --no-cache

install: install-dev install-docs install-application




install-enforce:
	@pre-commit install

install-docs:
	@uv pip install -r requirements-docs.txt --no-cache

docs:
	@echo "The internal documentation has been served at URL: \"http://127.0.0.1:2222\""
	@uv run -m mkdocs serve --dev-addr 0.0.0.0:2222 \
		--watch docs/ --watch mkdocs.yaml \
		--watch README.md --watch CHANGELOG.md --watch TODO.md \
		--dirty;

up:
	uvicorn entrypoint:app --reload --host 0.0.0.0 --port 6048 --workers 2 --no-server-header --no-date-header
