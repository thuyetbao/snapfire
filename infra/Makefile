#!/bin/bash

# Settings
SHELL := /bin/bash
.DEFAULT_GOAL := info

# Avoid
.PHONY: script

# The project name
PROJECT_NAME := "Infra"
PLATFORM := "Google Cloud Platform"

# Project ====================================================================================
# ============================================================================================

info:
	@echo -e ""
	@echo -e "========================================="
	@echo -e "\t\t\e[34m${PROJECT_NAME}\e[0m"
	@echo -e ""
	@echo -e "   Provider: ${PLATFORM}"
	@echo -e "========================================="
	@echo -e ""

# Provider: Cloud Platform ===================================================================
# ============================================================================================

# Setting
# gcloud config set account ${ACCOUNT_ID}
# gcloud config set project ${PROJECT_ID}
# gcloud config set compute/region ${PROJECT_REGION}
# gcloud config set compute/zone ${PROJECT_REGION}-a

auth-login:
	gcloud auth application-default login

auth-logout:
	gcloud auth application-default logout

auth: auth-login

auth-ls:
	gcloud auth list
