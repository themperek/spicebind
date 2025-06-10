# Makefile for spicebind VPI module

# Compiler and basic flags
CXX = g++
CXXFLAGS_COMMON = -shared -fPIC -std=c++17 -I./cpp

# Release and debug specific flags
CXXFLAGS_RELEASE = $(CXXFLAGS_COMMON) -O3 -DNDEBUG
CXXFLAGS_DEBUG = $(CXXFLAGS_COMMON) -g -O0 -DDEBUG

# Try to find ngspice paths automatically
NGSPICE_INCLUDE := $(shell \
	ngspice_exe=$$(which ngspice 2>/dev/null); \
	if [ -n "$$ngspice_exe" ]; then \
		base_dir=$$(dirname $$(dirname $$ngspice_exe)); \
		for dir in "$$base_dir/include" "$$base_dir/include/ngspice" /usr/include /usr/local/include /opt/homebrew/include; do \
			if [ -d "$$dir/ngspice" ] || [ -f "$$dir/ngspice.h" ]; then \
				echo "$$dir"; \
				break; \
			fi; \
		done; \
	else \
		for dir in /usr/include /usr/local/include /opt/homebrew/include; do \
			if [ -d "$$dir/ngspice" ] || [ -f "$$dir/ngspice.h" ]; then \
				echo "$$dir"; \
				break; \
			fi; \
		done; \
	fi)

NGSPICE_LIB := $(shell \
	ngspice_exe=$$(which ngspice 2>/dev/null); \
	if [ -n "$$ngspice_exe" ]; then \
		base_dir=$$(dirname $$(dirname $$ngspice_exe)); \
		for dir in "$$base_dir/lib" "$$base_dir/lib64" /usr/lib /usr/lib64 /usr/local/lib /opt/homebrew/lib; do \
			if [ -f "$$dir/libngspice.so" ] || [ -f "$$dir/libngspice.a" ]; then \
				echo "$$dir"; \
				break; \
			fi; \
		done; \
	else \
		for dir in /usr/lib /usr/lib64 /usr/local/lib /opt/homebrew/lib; do \
			if [ -f "$$dir/libngspice.so" ] || [ -f "$$dir/libngspice.a" ]; then \
				echo "$$dir"; \
				break; \
			fi; \
		done; \
	fi)

# Add ngspice paths if found
ifneq ($(NGSPICE_INCLUDE),)
	CXXFLAGS_COMMON += -I$(NGSPICE_INCLUDE)
endif

ifneq ($(NGSPICE_LIB),)
	LDFLAGS += -L$(NGSPICE_LIB)
endif

LDFLAGS += -lngspice

# Source files
SOURCES = cpp/SpiceVpiConfig.cpp \
          cpp/AnalogDigitalInterface.cpp \
          cpp/NgSpiceCallbacks.cpp \
          cpp/VpiCallbacks.cpp \
          cpp/vpi_module.cpp

# Object files
OBJECTS_RELEASE = $(SOURCES:.cpp=_release.o)
OBJECTS_DEBUG = $(SOURCES:.cpp=_debug.o)

# Output directory and target
OUTPUT_DIR = spicebind
TARGET = $(OUTPUT_DIR)/spicebind_vpi.vpi
TARGET_DEBUG = $(OUTPUT_DIR)/spicebind_vpi_debug.vpi

# Default target
all: release

# Release target
release: $(TARGET)

# Debug target
debug: $(TARGET_DEBUG)

# Create output directory
$(OUTPUT_DIR):
	mkdir -p $(OUTPUT_DIR)

# Release build
$(TARGET): $(OBJECTS_RELEASE) | $(OUTPUT_DIR)
	@echo "Building release VPI module..."
	$(CXX) $(CXXFLAGS_RELEASE) $(OBJECTS_RELEASE) -o $@ $(LDFLAGS)
	@echo "Successfully built release VPI module: $@"

# Debug build
$(TARGET_DEBUG): $(OBJECTS_DEBUG) | $(OUTPUT_DIR)
	@echo "Building debug VPI module..."
	$(CXX) $(CXXFLAGS_DEBUG) $(OBJECTS_DEBUG) -o $@ $(LDFLAGS)
	@echo "Successfully built debug VPI module: $@"

# Release object files
%_release.o: %.cpp
	@echo "Compiling $< (release)..."
	$(CXX) $(CXXFLAGS_RELEASE) -c $< -o $@

# Debug object files
%_debug.o: %.cpp
	@echo "Compiling $< (debug)..."
	$(CXX) $(CXXFLAGS_DEBUG) -c $< -o $@

# Clean targets
clean:
	rm -f $(OBJECTS_RELEASE) $(OBJECTS_DEBUG)

clean-all: clean
	rm -f $(TARGET) $(TARGET_DEBUG)

# Show detected ngspice paths
info:
	@echo "Detected ngspice paths:"
	@echo "  Include: $(NGSPICE_INCLUDE)"
	@echo "  Library: $(NGSPICE_LIB)"
	@echo "Source files: $(SOURCES)"
