// Makefile — drives xcrun metal + xcrun metallib for Qwen3.5 0.8B kernels
// Used by the Zig build (`make -C metal`) and also runnable directly:
//   make -C metal -f Makefile

# Configurable
SDK        ?= macosx
ARCH       ?= $(shell uname -m)
OPT_LEVEL  ?= -O3
MTL_FLAGS  ?= -std=metal3.0 -fno-fast-math -gline-tables

BUILD_DIR  ?= ../build
SRC_DIR    ?= .

SOURCES    := $(filter-out $(SRC_DIR)/kernels.metal,$(wildcard $(SRC_DIR)/*.metal))
OBJECTS    := $(patsubst $(SRC_DIR)/%.metal,$(BUILD_DIR)/%.air,$(SOURCES))
LIBRARY    := $(BUILD_DIR)/kernels.metallib

.PHONY: all clean

all: $(LIBRARY)

$(LIBRARY): $(OBJECTS)
	@mkdir -p $(BUILD_DIR)
	xcrun -sdk $(SDK) metallib $^ -o $@
	@echo "Built $@"

$(BUILD_DIR)/%.air: $(SRC_DIR)/%.metal
	@mkdir -p $(BUILD_DIR)
	xcrun -sdk $(SDK) metal $(MTL_FLAGS) $(OPT_LEVEL) -c $< -o $@
	@echo "Compiled $< -> $@"

clean:
	rm -rf $(BUILD_DIR)
