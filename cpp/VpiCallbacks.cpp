#include "VpiCallbacks.h"
#include "NgSpiceCallbacks.h"
#include "Debug.h"
#include "TimeBarrier.h"
#include "AnalogDigitalInterface.h"
#include "Config.h"
#include "ngspice/sharedspice.h"
#include "vpi_user.h"
#include <memory>
#include <exception>
#include <thread>
#include <chrono>
#include <cmath>

// External global variables (defined in vpi_module.cpp)
extern spice_vpi::TimeBarrier<unsigned long long> g_time_barrier;
extern spice_vpi::Config::Settings g_config;
extern std::unique_ptr<spice_vpi::AnalogDigitalInterface> g_interface;

// Global VPI state variables
static bool add_ngspice_timestep = false;
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
    DBG("enter %s current_time=%llu size=%d value=%f", name, current_time, vsize, val_s.value.real);


    // since we may go back in time in ngspice we need to remove the next time callback
    if (next_time_cb_handle != nullptr) {
        DBG("removing next_time_cb"); 
        // ngspice will update - cancel next time callback will be added in rw_sync
        // what if time_cb is registered for current time
        vpi_remove_cb(next_time_cb_handle);
        next_time_cb_handle = nullptr;
    }

    if (!add_ngspice_timestep) { // only once if multiple input changes same time
        DBG("register vpi_timestep_cb current_time=%llu next_time_spice=%lld", current_time, g_time_barrier.get_next_spice_step_time());

        // register next time callback for current time once
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

        vpi_register_cb(&next_cb_data);

        add_ngspice_timestep = true;

    }

    // Returning 0 keeps the callback installed (so it will fire again on the next value change)
    return 0;
}


auto vpi_timestep_cb(p_cb_data cb_data_p) -> PLI_INT32 {

    s_vpi_time simtime;
    simtime.type = vpiSimTime;
    vpi_get_time(nullptr, &simtime);
    unsigned long long current_time = (simtime.high * (1ULL << 32)) + simtime.low;

    DBG("enter current_time=%llu next_time_spice=%lld", current_time, g_time_barrier.get_next_spice_step_time());

    if (add_ngspice_timestep) {
        DBG("add ngspice time step at current_time=%llu", current_time);
        g_time_barrier.update_no_wait(spice_vpi::TimeBarrier<unsigned long long>::SPICE_ENGINE_ID, current_time);
        g_time_barrier.set_needs_redo(true);
    }

    g_time_barrier.update(spice_vpi::TimeBarrier<unsigned long long>::HDL_ENGINE_ID, current_time + 1);
    DBG("after time_sync.update (+1) current_time=%llu next_time_spice=%lld", current_time, g_time_barrier.get_next_spice_step_time());

    if (add_ngspice_timestep) {
        DBG("update_all_digital_inputs after ngspice time new timestep");
        g_interface->update_all_digital_inputs();

        // TODO: add one more ngspice step (+1) to have inputs rise faster?
    }
    add_ngspice_timestep = false;

    //
    //  update digital outputs
    //
    g_interface->set_digital_output();

    unsigned long long next_spice_step = g_time_barrier.get_next_spice_step_time();
    unsigned long long time_low = next_spice_step - current_time;

    if (time_low < 1) {
        DBG("SMALL STEP: current_time=%llu next_spice_step=%llu time_step==0", current_time, next_spice_step);
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
        
        // Log all HDL instances
        vpi_printf("** Info: Using HDL instances: ");
        for (size_t i = 0; i < g_config.hdl_instance_names.size(); ++i) {
            vpi_printf("%s", g_config.hdl_instance_names[i].c_str());
            if (i < g_config.hdl_instance_names.size() - 1) {
                vpi_printf(", ");
            }
        }
        if (g_config.full_path_discovery) {
            vpi_printf(" (full path discovery mode)");
        }
        vpi_printf("\n");
        
        vpi_printf("** Info: Using VCC: %g\n", g_config.vcc_voltage);
        vpi_printf("** Info: Using logic thresholds: LOGIC_THRESHOLD_LOW=%g, LOGIC_THRESHOLD_HIGH=%g\n", 
                   g_config.logic_threshold_low, g_config.logic_threshold_high);
        
        int time_unit = vpi_get(vpiTimeUnit, nullptr);
        int time_precision = vpi_get(vpiTimePrecision, nullptr);
        g_config.time_precision = static_cast<unsigned long long>(std::pow(10, -time_precision));
        vpi_printf("** Info: Simulation precision: %lld (10e%d)\n", g_config.time_precision, time_precision);
        
    } catch (const std::exception& e) {
        ERROR("Configuration error: %s", e.what());
        return 1;
    }

    // Process each HDL instance
    for (const std::string& instance_name : g_config.hdl_instance_names) {
        vpiHandle inst = vpi_handle_by_name(const_cast<char*>(instance_name.c_str()), nullptr);
        if (inst == nullptr) {
            ERROR("ERROR: instance \"%s\" not found", instance_name.c_str());
            continue; // Continue with other instances instead of returning
        }

        vpi_printf("** Info: Processing instance: %s\n", instance_name.c_str());

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
    }

    //
    // initialize ngspice
    //
    if (ngSpice_Init(ng_printf, nullptr, ng_exit, nullptr, nullptr, nullptr, nullptr) == 0) { 
        ngSpice_Command((char *)g_config.spice_netlist_path.c_str());
    } else {
        ERROR("Failed to initialize ngspice.");
        vpi_control(vpiFinish, 1);
        return 1;
    }

    if (ngSpice_Init_Sync(ng_srcdata, nullptr, ng_sync, nullptr, nullptr) == 0) {
        ngSpice_Command((char *)"bg_run");
        std::this_thread::sleep_for(std::chrono::seconds(1)); // wait for ngspice to start
        if (ngSpice_running()==0) {
            ERROR("Failed to initialize run ngspice.");
            vpi_control(vpiFinish, 1);
            return 1;
        }
    } else {
        ERROR("Failed to initialize ngSpice_Init_Sync interface.");
        vpi_control(vpiFinish, 1);
        return 1;
    }

    g_time_barrier.update(spice_vpi::TimeBarrier<unsigned long long>::HDL_ENGINE_ID, 1);
    DBG("update time_barrier.update t=%llu", 1);

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
