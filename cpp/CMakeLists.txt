cmake_minimum_required(VERSION 3.12)
project(fusehdl_vpi)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Set default build type to Release if not specified
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Compiler flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fPIC")
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 -DDEBUG")

# Find ngspice installation
find_program(NGSPICE_EXECUTABLE ngspice)

# Function to find ngspice paths
function(find_ngspice_paths)
    set(NGSPICE_INCLUDE_DIRS "")
    set(NGSPICE_LIBRARY_DIRS "")
    
    # If ngspice executable found, use its location as base
    if(NGSPICE_EXECUTABLE)
        get_filename_component(NGSPICE_BIN_DIR ${NGSPICE_EXECUTABLE} DIRECTORY)
        get_filename_component(NGSPICE_BASE_DIR ${NGSPICE_BIN_DIR} DIRECTORY)
        
        # Check for include directories
        set(INCLUDE_SEARCH_PATHS 
            "${NGSPICE_BASE_DIR}/include"
            "${NGSPICE_BASE_DIR}/include/ngspice"
        )
    endif()
    
    # Add common system paths
    list(APPEND INCLUDE_SEARCH_PATHS
        "/usr/include"
        "/usr/local/include"
        "/opt/homebrew/include"
    )
    
    # Find include directory
    foreach(dir ${INCLUDE_SEARCH_PATHS})
        if(IS_DIRECTORY "${dir}/ngspice" OR EXISTS "${dir}/ngspice.h")
            set(NGSPICE_INCLUDE_DIRS ${dir} PARENT_SCOPE)
            break()
        endif()
    endforeach()
    
    # Find library directory
    if(NGSPICE_EXECUTABLE)
        set(LIB_SEARCH_PATHS 
            "${NGSPICE_BASE_DIR}/lib"
            "${NGSPICE_BASE_DIR}/lib64"
        )
    endif()
    
    list(APPEND LIB_SEARCH_PATHS
        "/usr/lib"
        "/usr/lib64"
        "/usr/local/lib"
        "/opt/homebrew/lib"
    )
    
    foreach(dir ${LIB_SEARCH_PATHS})
        if(EXISTS "${dir}/libngspice.so" OR EXISTS "${dir}/libngspice.a")
            set(NGSPICE_LIBRARY_DIRS ${dir} PARENT_SCOPE)
            break()
        endif()
    endforeach()
endfunction()

# Find ngspice paths
find_ngspice_paths()

# Display found paths
message(STATUS "Detected ngspice paths:")
message(STATUS "  Include: ${NGSPICE_INCLUDE_DIRS}")
message(STATUS "  Library: ${NGSPICE_LIBRARY_DIRS}")

# Source files
set(SOURCES
    SpiceVpiConfig.cpp
    AnalogDigitalInterface.cpp
    NgSpiceCallbacks.cpp
    VpiCallbacks.cpp
    vpi_module.cpp
)

# Create shared library
add_library(fusehdl_vpi SHARED ${SOURCES})

# Set library properties
set_target_properties(fusehdl_vpi PROPERTIES
    PREFIX ""
    SUFFIX ".vpi"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../fusehdl"
)

# Include directories
target_include_directories(fusehdl_vpi PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# Add ngspice include directory if found
if(NGSPICE_INCLUDE_DIRS)
    target_include_directories(fusehdl_vpi PRIVATE ${NGSPICE_INCLUDE_DIRS})
endif()

# Add ngspice library directory if found
if(NGSPICE_LIBRARY_DIRS)
    target_link_directories(fusehdl_vpi PRIVATE ${NGSPICE_LIBRARY_DIRS})
endif()

# Link with ngspice library
target_link_libraries(fusehdl_vpi PRIVATE ngspice)

# Create output directory
file(MAKE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../fusehdl")

# Add debug variant
add_library(fusehdl_vpi_debug SHARED ${SOURCES})
set_target_properties(fusehdl_vpi_debug PROPERTIES
    PREFIX ""
    SUFFIX ".vpi"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../fusehdl"
    COMPILE_FLAGS "-g -O0 -DDEBUG"
)

target_include_directories(fusehdl_vpi_debug PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

if(NGSPICE_INCLUDE_DIRS)
    target_include_directories(fusehdl_vpi_debug PRIVATE ${NGSPICE_INCLUDE_DIRS})
endif()

if(NGSPICE_LIBRARY_DIRS)
    target_link_directories(fusehdl_vpi_debug PRIVATE ${NGSPICE_LIBRARY_DIRS})
endif()

target_link_libraries(fusehdl_vpi_debug PRIVATE ngspice)

# Export compile commands for clang-based tools (clang-tidy, VS Code, etc.)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Print build information
message(STATUS "Source files: ${SOURCES}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Output directory: ${CMAKE_CURRENT_SOURCE_DIR}/../fusehdl") 