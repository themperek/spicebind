cmake_minimum_required(VERSION 3.15)
project(spicebind_vpi LANGUAGES CXX)


# Call CMake with:  cmake -DNGSPICE_ROOT=/path/to/ngspice <src_dir>
set(NGSPICE_ROOT "" CACHE PATH
    "Root of an NGSpice installation containing include/ and lib/."
)

if(NOT NGSPICE_ROOT)
    # Try to locate the ngspice executable first
    find_program(NGSPICE_EXE
        NAMES ngspice          # ngspice.exe on Windows is also matched
        DOC   "Full path to the ngspice executable"
    )

    if(NGSPICE_EXE)
        # bin  -> parent -> install root
        get_filename_component(NGSPICE_BIN_DIR "${NGSPICE_EXE}" DIRECTORY)
        get_filename_component(NGSPICE_ROOT    "${NGSPICE_BIN_DIR}" DIRECTORY)

        message(STATUS "Found ngspice executable:  ${NGSPICE_EXE}")
        message(STATUS "Inferred NGSPICE_ROOT:     ${NGSPICE_ROOT}")
    # else()
    #     message(FATAL_ERROR
    #         "Could not find 'ngspice' in your PATH and NGSPICE_ROOT was not "
    #         "given.  Either install NGSpice or run CMake with "
    #         "-DNGSPICE_ROOT=/path/to/ngspice."
    #     )
    endif()
endif()


# ---------------------------------------------------------------------------
#  Source files and common configuration
# ---------------------------------------------------------------------------
set(SPICEBIND_SRC
    cpp/Config.cpp
    cpp/AnalogDigitalInterface.cpp
    cpp/NgSpiceCallbacks.cpp
    cpp/VpiCallbacks.cpp
    cpp/vpi_module.cpp
)

set(_ngspice_possible_libdirs
    "${NGSPICE_ROOT}/lib"
)

# Function to configure a VPI target with common settings
function(configure_vpi_target target_name)
    set_target_properties(${target_name} PROPERTIES
        CXX_STANDARD 17
        POSITION_INDEPENDENT_CODE ON
        PREFIX ""          # stop CMake from adding "lib"
        SUFFIX ".vpi"      # final name: ${target_name}.vpi
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/spicebind"
    )

    target_include_directories(${target_name}
        PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/cpp
            ${NGSPICE_ROOT}/include
    )

    target_link_directories(${target_name} PRIVATE ${_ngspice_possible_libdirs})
    target_link_libraries(${target_name} PRIVATE ngspice)
endfunction()

# ---------------------------------------------------------------------------
#  RELEASE variant
# ---------------------------------------------------------------------------
add_library(spicebind_vpi SHARED ${SPICEBIND_SRC})
configure_vpi_target(spicebind_vpi)

# ---------------------------------------------------------------------------
#  DEBUG variant
# ---------------------------------------------------------------------------
add_library(spicebind_vpi_debug SHARED ${SPICEBIND_SRC})
configure_vpi_target(spicebind_vpi_debug)

# ► debug-specific compile flags ◄
target_compile_definitions(spicebind_vpi_debug PRIVATE DEBUG)
target_compile_options(spicebind_vpi_debug PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/Zi /Od>
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-g -O0>
)

# convenience meta-target:  cmake --build . --target debug
add_custom_target(debug ALL DEPENDS spicebind_vpi_debug)

# ---------------------------------------------------------------------------
#  Installation for Python packaging
# ---------------------------------------------------------------------------
# Install VPI files to the Python package directory
install(FILES 
    $<TARGET_FILE:spicebind_vpi>
    $<TARGET_FILE:spicebind_vpi_debug>
    DESTINATION spicebind
    COMPONENT python_package
)