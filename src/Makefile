UV ?= uv
PY_VERSION := 3.12

# Cross-build target (keep Lambdas on x86_64)
TARGET_PLATFORM := x86_64-manylinux2014
TARGET_ONLY_BINARY := :all:

# Código raíz = src/ (ubicación de este Makefile)
CODE_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
# Backend root (pyproject vive aquí)
PROJECT_ROOT := $(abspath $(CODE_ROOT)/rest_api)
COMMONS_PACKAGE := $(abspath $(CODE_ROOT)/commons)
PYPROJECT := $(PROJECT_ROOT)/pyproject.toml


# Salida de sam build
SAM_BUILD_DIR ?= $(PROJECT_ROOT)/.aws-sam/build

# Cache local de dependencias
DEPS_DIR ?= $(CODE_ROOT)/../build
REQ_FILE := $(DEPS_DIR)/requirements.txt
DEPS_SENTINEL := $(DEPS_DIR)/.deps_built
REBUILD_DEPS ?= false

FUNCTIONS := \
	SendChannelMessageFunction \
	SendChannelMessageWebsocketFunction \
	GetChannelMessagesFunction \
	AgentFunction \
	DeliveryFunction

BUILD_TARGETS := $(addprefix build-,$(FUNCTIONS))

.PHONY: deps copy-deps $(FUNCTIONS) $(BUILD_TARGETS)

# Construye dependencias a partir de src/rest_api/pyproject.toml usando uv
ECHO_SEP = echo "------------------------------------------------------------"
ECHO = echo "==> "

deps:
	@mkdir -p "$(DEPS_DIR)"
	@if [ "$(REBUILD_DEPS)" = "true" ]; then rm -f "$(DEPS_SENTINEL)"; fi
	@if [ ! -f "$(DEPS_SENTINEL)" ]; then \
		$(ECHO_SEP); \
		$(ECHO) "[deps] Exporting requirements from $(PYPROJECT)"; \
		cd "$(PROJECT_ROOT)" && $(UV) export --frozen --quiet --format requirements-txt --output-file "$(REQ_FILE)" --project "$(PYPROJECT)" --no-hashes --no-dev --no-annotate --no-header; \
		$(ECHO) "[deps] Installing (platform=$(TARGET_PLATFORM) impl=$(TARGET_IMPL) py=$(PY_VERSION)) into $(DEPS_DIR)"; \
		cd "$(PROJECT_ROOT)" && $(UV) pip install --python-platform "$(TARGET_PLATFORM)" --python-version "$(PY_VERSION)" --only-binary="$(TARGET_ONLY_BINARY)" --target "$(DEPS_DIR)" -r "$(REQ_FILE)" --no-cache; \
		$(ECHO) "[deps] Cleaning bytecode"; \
		find "$(DEPS_DIR)" -name "__pycache__" -prune -exec rm -rf {} +; \
		find "$(DEPS_DIR)" -name "*.pyc" -delete; \
		$(ECHO) "[deps] Done"; \
		$(ECHO_SEP); \
		touch "$(DEPS_SENTINEL)"; \
	fi

# Copia las dependencias construidas a cada función lambda ya generada por sam build
define COPY_DEPS_FN
$(1): deps
	@target_dir="$(SAM_BUILD_DIR)/$(1)"; \
	if [ ! -d "$$target_dir" ]; then \
		echo "Build output for $(1) not found at $$target_dir; run 'sam build $(1)' first."; \
		exit 1; \
	fi; \
	echo "Copying dependencies into $$target_dir"; \
	cp -a "$(DEPS_DIR)/." "$$target_dir/"
endef

$(foreach fn,$(FUNCTIONS),$(eval $(call COPY_DEPS_FN,$(fn))))

# Copia deps a todas las funciones lambda
copy-deps: $(FUNCTIONS)

clean-deps:
	$(ECHO) "[deps] Deleted dependencies directory"; \
	@rm -rf "$(DEPS_DIR)"

#
# Targets que usa SAM CustomMakeBuilder (BuildTarget: build-<FunctionName>)
#

# Defaults when SAM does not inject SOURCE_DIR/ARTIFACTS_DIR
SOURCE_DIR ?= $(PROJECT_ROOT)
SOURCE_DIR ?= $(PROJECT_ROOT)
ARTIFACTS_DIR ?= $(PROJECT_ROOT)/.aws-sam/build/manual

define BUILD_FN
build-$(1): deps
	@$(ECHO_SEP)
	@$(ECHO) "[build $(1)] Target: $(ARTIFACTS_DIR)"
	@rm -rf "$(ARTIFACTS_DIR)"
	@mkdir -p "$(ARTIFACTS_DIR)"
	@$(ECHO) "  [deps] -> $(ARTIFACTS_DIR)"; \
	cp -a "$(DEPS_DIR)/." "$(ARTIFACTS_DIR)/"
	@$(ECHO) "  [source] -> $(ARTIFACTS_DIR)"; \
	cp -a "$(SOURCE_DIR)" "$(ARTIFACTS_DIR)/"
	@$(ECHO) "  [commons] -> $(ARTIFACTS_DIR)"; \
	cp -r "$(COMMONS_PACKAGE)" "$(ARTIFACTS_DIR)/"
	@$(ECHO) "  [clean] prune pyc/__pycache__"
	@find "$(ARTIFACTS_DIR)" -name "__pycache__" -prune -exec rm -rf {} +
	@find "$(ARTIFACTS_DIR)" -name "*.pyc" -delete
	@$(ECHO) "[build $(1)] Done"
	@$(ECHO_SEP)
endef

$(foreach fn,$(FUNCTIONS),$(eval $(call BUILD_FN,$(fn))))