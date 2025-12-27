#!/bin/bash

# Setting
.DEFAULT_GOAL := info
SHELL := /bin/bash

.PHONY: venv

# The local public IP address (using for development mode only)
LOCAL_PUBLIC_IP := $(shell curl -s https://api.ipify.org)

# ==============================================================================
# Project ======================================================================
# ==============================================================================

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

install-enforce:
	@pre-commit install

venv:
	@uv venv --allow-existing --color "auto" --python 3.12.10 --seed venv

install-dev:
	@uv pip install "pip>=24.3.1,<=25.0.10" "setuptools>=75.8.0,<78.0.0" "wheel>=0.45.1,<0.50.0" "hatch>=1.12.1,<1.15.0" --no-cache
	@uv pip install -r requirements-dev.txt --no-cache

install-provision:
	@uv pip install -r provision/probe/requirements.txt -r provision/target/requirements.txt --no-cache

install-docs:
	@uv pip install -r requirements-docs.txt --no-cache

install: install-dev install-provision install-docs

up-docs:
	@echo "The internal documentation has been served at URL: \"http://127.0.0.1:7777\""
	@uv run -m mkdocs serve --dev-addr 0.0.0.0:7777 \
		--watch docs/ --watch mkdocs.yaml \
		--watch README.md --watch CHANGELOG.md --watch TODO.md \
		--dirty;

up-probe-agent:
	cd provision/probe && \
		DATA_MEASUREMENT_DATA_JSONL_PATH=data/measurement.jsonl uvicorn agent:app --reload --host 0.0.0.0 --port 8888 \
			--workers 1 --no-server-header --no-date-header

up-probe-collector:
	cd provision/probe && \
		python collector.py \
			--ip ${LOCAL_PUBLIC_IP} \
			--output data/test.jsonl \
			--set "tcp_port=80" \
			--set "udp_port=53" \
			--set "http_port=4200" --set "http_path=//health" --set "http_scheme=http"

up-target-exposer:
	cd provision/target && \
		uvicorn exposer:app --reload --host 0.0.0.0 --port 9999 \
			--workers 1 --no-server-header --no-date-header
