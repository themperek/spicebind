#include "VpiCallbacks.h"
#include "NgSpiceCallbacks.h"
#include "Debug.h"
#include "TimeBarrier.h"
#include "AnalogDigitalInterface.h"
#include "SpiceVpiConfig.h"
#include "ngspice/sharedspice.h"
#include <memory>
#include <exception>

// External global variables (defined in vpi_module.cpp)
extern spice_vpi::TimeBarrier<unsigned long long> g_time_barrier;
extern spice_vpi::Config::Settings g_config;
extern std::unique_ptr<spice_vpi::AnalogDigitalInterface> g_interface;

// Global VPI state variables
static bool rw_sync_done = false;
static vpiHandle next_time_cb_handle;

namespace spice_vpi {

void register_vpi_callbacks() {
    s_cb_data cb_data;

    /* Simulation start */
    cb_data.reason = cbStartOfSimulation;
    cb_data.cb_rtn = vpi_start_of_sim_cb;
    cb_data.obj = nullptr;
    cb_data.time = nullptr;
    cb_data.value = nullptr;
    vpi_register_cb(&cb_data);

    /* End of simulation */
    cb_data.reason = cbEndOfSimulation;
    cb_data.cb_rtn = vpi_end_of_sim_cb;
    vpi_register_cb(&cb_data);
}

auto vpi_port_change_cb(p_cb_data cb_data_p) -> PLI_INT32 {

    vpiHandle value_handle = cb_data_p->obj;

    const char *name = vpi_get_str(vpiName, value_handle);
    int vsize = vpi_get(vpiSize, value_handle);
    s_vpi_value val_s;
    val_s.format = vpiRealVal; // get it as an integer (0 or 1 for a 1-bit signal)
    vpi_get_value(value_handle, &val_s);
    s_vpi_time simtime;
    simtime.type = vpiSimTime;
    vpi_get_time(nullptr, &simtime);
    unsigned long long current_time = (simtime.high * (1ULL << 32)) + simtime.low;
    DBG("enter %s size=%d value=%f t=%llu", name, vsize, val_s.value.real, current_time);

    if (next_time_cb_handle != nullptr) {
        DBG("removing next_time_cb"); // ngspice will update - cancel next time callback will be added in rw_sync
        vpi_remove_cb(next_time_cb_handle);
        next_time_cb_handle = nullptr;
    }

    if (!rw_sync_done) { // only once if multiple input changes same time
        DBG("register cbReadOnlySynch");
        s_vpi_time time_data;
        time_data.type = vpiSimTime;
        time_data.high = 0;
        time_data.low = 0;
        time_data.real = 0;

        s_cb_data cb_data_next;
        cb_data_next.reason = cbReadOnlySynch;
        cb_data_next.cb_rtn = vpi_rw_sync_cb;
        cb_data_next.obj = nullptr;
        cb_data_next.time = &time_data;
        cb_data_next.value = nullptr;
        cb_data_next.index = 0;
        cb_data_next.user_data = nullptr;

        vpi_register_cb(&cb_data_next);
        rw_sync_done = true;
    }

    //
    //  read/update digital values
    //

    g_interface->digital_input_update(value_handle);

    // Returning 0 keeps the callback installed (so it will fire again on the next value change)
    return 0;
}

auto vpi_rw_sync_cb(p_cb_data cb_data_p) -> PLI_INT32 {

    rw_sync_done = false;

    s_vpi_time simtime;
    simtime.type = vpiSimTime;
    vpi_get_time(nullptr, &simtime);
    unsigned long long current_time = (simtime.high * (1ULL << 32)) + simtime.low;

    DBG("enter t=%llu next_time_spice=%lld", current_time, g_time_barrier.get_next_spice_step_time());

    // manage wait time for ngspice to redo last step
    g_time_barrier.update_no_wait(spice_vpi::TimeBarrier<unsigned long long>::SPICE_ENGINE_ID, current_time);

    DBG("set redo step");

    g_time_barrier.set_needs_redo(true);

    g_time_barrier.update(spice_vpi::TimeBarrier<unsigned long long>::HDL_ENGINE_ID, current_time + 1);

    DBG("aftertime_sync.update t=%llu", current_time + 1);

    s_vpi_time next_delay;
    next_delay.type = vpiSimTime;
    next_delay.high = 0;
    next_delay.low = 1; //-> update in the next step time

    s_cb_data next_cb_data;
    next_cb_data.reason = cbAfterDelay;    // cbReadWriteSynch;
    next_cb_data.cb_rtn = vpi_timestep_cb; // call this function again -> this is wrong, it should be cbNextSimTime
    next_cb_data.obj = nullptr;
    next_cb_data.time = &next_delay;
    next_cb_data.value = nullptr;

    next_time_cb_handle = vpi_register_cb(&next_cb_data);

    return 0;
}

auto vpi_timestep_cb(p_cb_data cb_data_p) -> PLI_INT32 {

    s_vpi_time simtime;
    simtime.type = vpiSimTime;
    vpi_get_time(nullptr, &simtime);
    unsigned long long current_time = (simtime.high * (1ULL << 32)) + simtime.low;

    DBG("enter t=%llu next_time_spice=%lld", current_time, g_time_barrier.get_next_spice_step_time());

    g_time_barrier.update(spice_vpi::TimeBarrier<unsigned long long>::HDL_ENGINE_ID, current_time + 1);

    DBG("after time_sync.update t=%llu next_time_spice=%lld", current_time + 1, g_time_barrier.get_next_spice_step_time());

    //
    //  update digital outputs
    //
    g_interface->set_digital_output();

    unsigned long long next_spice_step = g_time_barrier.get_next_spice_step_time();
    unsigned long long time_low = next_spice_step - current_time;

    // TODO: something is wrong here
    if (time_low < 1) {
        ERROR(" t=%llu next_spice_step=%llu time_step==0", current_time, next_spice_step);
        time_low = 1;
    }

    cb_data_p->reason = cbAfterDelay;
    cb_data_p->cb_rtn = vpi_timestep_cb; // call this function again

    cb_data_p->time->type = vpiSimTime;
    cb_data_p->time->high = 0;
    cb_data_p->time->low = time_low;

    DBG("register next event t=%llu time_low=%llu next_time_spice=%lld", current_time, time_low, g_time_barrier.get_next_spice_step_time());

    next_time_cb_handle = vpi_register_cb(cb_data_p);

    return 0;
}

auto vpi_start_of_sim_cb(p_cb_data cb_data_p) -> PLI_INT32 {

    try {
        // Load configuration from environment variables
        g_config = spice_vpi::Config::load_from_environment();
        
        // Initialize the interface with the configuration
        g_interface = std::make_unique<spice_vpi::AnalogDigitalInterface>(g_config);
        
        vpi_printf("** Info: Using SPICE netlist: %s\n", g_config.spice_netlist_path.c_str());
        vpi_printf("** Info: Using HDL instance: %s\n", g_config.hdl_instance_name.c_str());
        vpi_printf("** Info: Using VCC: %g\n", g_config.vcc_voltage);
        vpi_printf("** Info: Using logic thresholds: low=%g, high=%g\n", 
                   g_config.logic_threshold_low, g_config.logic_threshold_high);
        
    } catch (const std::exception& e) {
        ERROR("Configuration error: %s", e.what());
        return 1;
    }

    vpiHandle inst = vpi_handle_by_name(const_cast<char*>(g_config.hdl_instance_name.c_str()), nullptr);
    if (inst == nullptr) {
        ERROR("ERROR: instance \"%s\" not found", g_config.hdl_instance_name.c_str());
        return 0;
    }

    vpiHandle iter = vpi_iterate(vpiPort, inst);
    vpiHandle port = nullptr;
    while ((port = vpi_scan(iter)) != nullptr) {

        const char *pname = vpi_get_str(vpiName, port);
        int dir = vpi_get(vpiDirection, port);

        if (dir == vpiInout) {
            ERROR(" port %s inout - not supported", pname);
        } else {
            g_interface->add_port(port);

            vpiHandle module = vpi_handle(vpiParent, port);
            vpiHandle net = vpi_handle_by_name(const_cast<char*>(pname), module);
            if (dir == vpiInput) {
                // Set up a value-change callback on that handle
                s_cb_data cb_data_s;
                cb_data_s.reason = cbValueChange;
                cb_data_s.cb_rtn = vpi_port_change_cb;
                cb_data_s.obj = net;
                cb_data_s.time = nullptr;
                cb_data_s.value = nullptr;
                vpi_register_cb(&cb_data_s);
            }
        }
    }

    //
    // initialize ngspice
    //
    if (ngSpice_Init(ng_printf, nullptr, ng_exit, nullptr, nullptr, nullptr, nullptr) == 0) { 
        ngSpice_Command((char *)g_config.spice_netlist_path.c_str());
    } else {
        ERROR("Failed to initialize ngspice.");
        return 1;
    }

    if (ngSpice_Init_Sync(ng_srcdata, nullptr, ng_sync, nullptr, nullptr) == 0) {
        ngSpice_Command((char *)"bg_run");
        if (ngSpice_running()==0) {
            ERROR("Failed to initialize run ngspice.");
            return 1;
        }
    } else {
        ERROR("Failed to initialize ngSpice_Init_Sync interface.");
        return 1;
    }

    g_time_barrier.update(spice_vpi::TimeBarrier<unsigned long long>::HDL_ENGINE_ID, 1);

    s_vpi_time next_delay;
    next_delay.type = vpiSimTime;
    next_delay.high = 0;
    next_delay.low = 0;

    s_cb_data next_cb_data;
    next_cb_data.reason = cbAfterDelay;
    next_cb_data.cb_rtn = vpi_timestep_cb;
    next_cb_data.obj = nullptr;
    next_cb_data.time = &next_delay;
    next_cb_data.value = nullptr;

    // vpi_timestep_cb(&next_cb_data);
    next_time_cb_handle = vpi_register_cb(&next_cb_data);

    return 0;
}

auto vpi_end_of_sim_cb(p_cb_data cb_data_p) -> PLI_INT32 {

    g_time_barrier.shutdown();

    ngSpice_Command((char *)"bg_halt");
    // ngSpice_Command((char *)"set filetype=ascii");
    ngSpice_Command((char *)"write dump.raw");

    vpi_printf("End of simulation\n");

    return 0;
}

} // namespace spice_vpi 