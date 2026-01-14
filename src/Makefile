UV ?= uv
PY_VERSION := 3.12

# Cross-build target (keep Lambdas on x86_64)
TARGET_PLATFORM := x86_64-manylinux2014
TARGET_ONLY_BINARY ?= :all:
TARGET_IMPLEMENTATION ?= cp

# Paths
CODE_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(abspath $(CODE_ROOT)/..)
PROJECT_ROOT := $(abspath $(CODE_ROOT)/rest_api)
COMMONS_PACKAGE := $(abspath $(CODE_ROOT)/commons)
PYPROJECT := $(PROJECT_ROOT)/pyproject.toml

# sam build output to repo root
SAM_ROOT ?= $(REPO_ROOT)/.aws_sam
SAM_BUILD_DIR ?= $(SAM_ROOT)/build

# Local dependency cache
DEPS_DIR ?= $(abspath $(REPO_ROOT)/build)
REQ_FILE := $(DEPS_DIR)/requirements.txt
DEPS_SENTINEL := $(abspath $(DEPS_DIR)/.deps_built)
REBUILD_DEPS ?= false

FUNCTIONS := \
	SendChannelMessageFunction \
	SendChannelMessageWebsocketFunction \
	GetChannelMessagesFunction \
	AgentFunction \
	DeliveryFunction

BUILD_TARGETS := $(addprefix build-,$(FUNCTIONS))

.PHONY: deps $(BUILD_TARGETS)

# Build dependencies from src/rest_api/pyproject.toml using uv
ECHO_SEP = echo "------------------------------------------------------------"
ECHO = echo "==> "

deps:
	@mkdir -p "$(DEPS_DIR)"
	@if [ "$(REBUILD_DEPS)" = "true" ]; then rm -f "$(DEPS_SENTINEL)"; fi
	@if [ -f "$(DEPS_SENTINEL)" ]; then \
		$(ECHO_SEP); \
		$(ECHO) "[deps] Using cached deps at $(DEPS_DIR)"; \
		$(ECHO_SEP); \
		exit 0; \
	fi
	@$(ECHO_SEP); \
	$(ECHO) "[deps] Exporting requirements from $(PYPROJECT)"; \
	cd "$(PROJECT_ROOT)" && $(UV) export --frozen --quiet --format requirements-txt --output-file "$(REQ_FILE)" --project "$(PYPROJECT)" --no-hashes --no-dev --no-annotate --no-header; \
	$(ECHO) "[deps] Installing (platform=$(TARGET_PLATFORM) impl=$(TARGET_IMPLEMENTATION) py=$(PY_VERSION)) into $(DEPS_DIR)"; \
	cd "$(PROJECT_ROOT)" && $(UV) pip install --python-platform "$(TARGET_PLATFORM)" --python-version "$(PY_VERSION)" --implementation "$(TARGET_IMPLEMENTATION)" --only-binary="$(TARGET_ONLY_BINARY)" --target "$(DEPS_DIR)" -r "$(REQ_FILE)" --no-cache; \
	$(ECHO) "[deps] Cleaning bytecode"; \
	find "$(DEPS_DIR)" -name "__pycache__" -prune -exec rm -rf {} +; \
	find "$(DEPS_DIR)" -name "*.pyc" -delete; \
	$(ECHO) "[deps] Done"; \
	$(ECHO_SEP); \
	touch "$(DEPS_SENTINEL)"

#
# Targets used by SAM CustomMakeBuilder (BuildTarget: build-<FunctionName>)
#

# Defaults when SAM does not inject SOURCE_DIR/ARTIFACTS_DIR
SOURCE_DIR ?= $(PROJECT_ROOT)
ARTIFACTS_DIR ?= $(SAM_BUILD_DIR)/manual

define BUILD_FN
build-$(1): deps
	@$(ECHO_SEP)
	@$(ECHO) "[build $(1)] Target: $(ARTIFACTS_DIR)"
	@rm -rf "$(ARTIFACTS_DIR)"
	@mkdir -p "$(ARTIFACTS_DIR)"
	@$(ECHO) "  [deps] -> $(ARTIFACTS_DIR)"; \
	cp -a "$(DEPS_DIR)/." "$(ARTIFACTS_DIR)/"
	@$(ECHO) "  [source] -> $(ARTIFACTS_DIR)"; \
	cp -a "$(SOURCE_DIR)/." "$(ARTIFACTS_DIR)/"
	@$(ECHO) "  [commons] -> $(ARTIFACTS_DIR)"; \
	cp -a "$(COMMONS_PACKAGE)/." "$(ARTIFACTS_DIR)/commons/"
	@$(ECHO) "  [clean] prune pyc/__pycache__"
	@find "$(ARTIFACTS_DIR)" -name "__pycache__" -prune -exec rm -rf {} +
	@find "$(ARTIFACTS_DIR)" -name "*.pyc" -delete
	@$(ECHO) "[build $(1)] Done"
	@$(ECHO_SEP)
endef

$(foreach fn,$(FUNCTIONS),$(eval $(call BUILD_FN,$(fn))))