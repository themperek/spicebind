
#include "TimeBarrier.h"
#include "Config.h"
#include "AnalogDigitalInterface.h"

#include "VpiCallbacks.h"

// Global variables
spice_vpi::TimeBarrier<unsigned long long> g_time_barrier;
spice_vpi::Config::Settings g_config;
std::unique_ptr<spice_vpi::AnalogDigitalInterface> g_interface;

/* This array tells Icarus which init function(s) to call */
void (*vlog_startup_routines[])(void) = {
    spice_vpi::register_vpi_callbacks,
    nullptr
};

// Build command:
// g++ -shared -fPIC -std=c++17 -I./cpp -I/home/tomasz.hemperek/miniconda3/include -L/home/tomasz.hemperek/miniconda3/lib -lngspice cpp/Config.cpp cpp/AnalogDigitalInterface.cpp cpp/NgSpiceCallbacks.cpp cpp/VpiCallbacks.cpp cpp/vpi_module.cpp -o spicebind/spicebind_vpi.vpi

// Build command profiler:
// g++ -shared -fPIC -std=c++17 -g -lprofiler -I./cpp -I/home/tomasz.hemperek/miniconda3/include -L/home/tomasz.hemperek/miniconda3/lib -lngspice cpp/Config.cpp cpp/AnalogDigitalInterface.cpp cpp/NgSpiceCallbacks.cpp cpp/VpiCallbacks.cpp cpp/vpi_module.cpp -o spicebind/spicebind_vpi.vpi  
// CPUPROFILE=./myprof.prof  python examples/adc/test_flash_adc8.py
// pprof --cum  --line --text spicebind/spicebind_vpi.vpi sim_build/myprof.prof > profline

// Usage:
// iverilog tests/tb.sv -o tests/tb
// SPICE_NETLIST=./tests/test.cir HDL_INSTANCE=tb.adc vvp -M ./fusehdl -m fusehdl_vpi tests/tb

// To visualize results:
// spyci -r tests/fadc.raw -o tests/myplot.png "v(in)"
