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
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

// External global variables (defined in vpi_module.cpp)
extern spice_vpi::TimeBarrier<unsigned long long> g_time_barrier;
extern spice_vpi::Config::Settings g_config;
extern std::unique_ptr<spice_vpi::AnalogDigitalInterface> g_interface;

// Global VPI state variables
static bool add_ngspice_timestep = false;
static vpiHandle next_time_cb_handle;
static bool g_is_verilator = false;
// Verilator keeps the user s_cb_data.time pointer (it does not copy the
// s_vpi_time). Icarus copies it. A single static time object is overwritten
// when a second callback is registered, which makes cbAfterDelay fire with
// delay 0 and skip the analog update window.
static std::vector<std::unique_ptr<s_vpi_time>> g_cb_times;

static vpiHandle find_hdl_instance(const std::string &instance_name) {
    vpiHandle inst = vpi_handle_by_name(const_cast<char *>(instance_name.c_str()), nullptr);
    if (inst == nullptr && instance_name.compare(0, 4, "TOP.") != 0) {
        const std::string with_top = "TOP." + instance_name;
        inst = vpi_handle_by_name(const_cast<char *>(with_top.c_str()), nullptr);
    }
    if (inst == nullptr && instance_name.compare(0, 4, "TOP.") == 0) {
        inst = vpi_handle_by_name(const_cast<char *>(instance_name.c_str() + 4), nullptr);
    }
    return inst;
}

static vpiHandle schedule_vpi_cb(PLI_INT32 reason, PLI_UINT32 delay_low,
                                 PLI_INT32 (*cb_rtn)(p_cb_data)) {
    auto time = std::make_unique<s_vpi_time>();
    time->type = vpiSimTime;
    time->high = 0;
    time->low = delay_low;
    s_cb_data next_cb_data{};
    next_cb_data.reason = reason;
    next_cb_data.cb_rtn = cb_rtn;
    next_cb_data.obj = nullptr;
    next_cb_data.time = time.get();
    next_cb_data.value = nullptr;
    vpiHandle handle = vpi_register_cb(&next_cb_data);
    g_cb_times.push_back(std::move(time));
    return handle;
}

static PLI_INT32 vpi_flush_outputs_cb(p_cb_data cb_data_p) {
    (void)cb_data_p;
    if (g_interface) {
        g_interface->set_digital_output();
    }
    return 0;
}

static vpiHandle schedule_timestep_cb(PLI_UINT32 delay_low) {
    return schedule_vpi_cb(cbAfterDelay, delay_low, spice_vpi::vpi_timestep_cb);
}

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
    const int obj_type = vpi_get(vpiType, value_handle);
    s_vpi_time simtime;
    simtime.type = vpiSimTime;
    vpi_get_time(nullptr, &simtime);
    unsigned long long current_time = (simtime.high * (1ULL << 32)) + simtime.low;
    s_vpi_value val_s;
    if (obj_type == vpiRealVar) {
        val_s.format = vpiRealVal;
        vpi_get_value(value_handle, &val_s);
        DBG("enter %s current_time=%llu size=%d value=%f", name, current_time, vsize, val_s.value.real);
    } else {
        val_s.format = vpiIntVal;
        vpi_get_value(value_handle, &val_s);
        DBG("enter %s current_time=%llu size=%d value=%d", name, current_time, vsize, val_s.value.integer);
    }


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

        // Verilator --main already called callTimedCbs this cycle, so a 0-delay
        // cbAfterDelay is not run until after time has moved. cbReadWriteSynch
        // still runs later in the same slot, before time advances.
        if (g_is_verilator) {
            schedule_vpi_cb(cbReadWriteSynch, 0, spice_vpi::vpi_timestep_cb);
        } else {
            schedule_timestep_cb(0);
        }

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

    // Verilator applies cocotb writes after ico, so cbValueChange on the
    // instance net often still sees the old value. Sample TOP/parent first.
    if (g_is_verilator) {
        g_interface->update_all_digital_inputs();
    }

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
    // Verilator --binary eval order is ico (parent = instance) then timing
    // resume (#delay checks). AfterDelay runs before eval, so a put there
    // makes delay-chain bits visible one sample early. Put after eval
    // (cbReadWriteSynch). Instance regs still hold the previous sample for ico.
    if (g_is_verilator && cb_data_p != nullptr && cb_data_p->reason == cbAfterDelay) {
        schedule_vpi_cb(cbReadWriteSynch, 0, vpi_flush_outputs_cb);
    } else {
        g_interface->set_digital_output();
    }

    unsigned long long next_spice_step = g_time_barrier.get_next_spice_step_time();
    unsigned long long time_low = 1;
    if (next_spice_step > current_time) {
        time_low = next_spice_step - current_time;
    }

    if (time_low < 1) {
        DBG("SMALL STEP: current_time=%llu next_spice_step=%llu time_step==0", current_time, next_spice_step);
        time_low = 1;
    }

    DBG("register next event t=%llu time_low=%llu next_time_spice=%lld", current_time, time_low, g_time_barrier.get_next_spice_step_time());

    next_time_cb_handle = schedule_timestep_cb(static_cast<PLI_UINT32>(time_low));

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

    s_vpi_vlog_info vlog_info{};
    g_is_verilator
        = (vpi_get_vlog_info(&vlog_info) != 0 && vlog_info.product != nullptr
           && std::strstr(vlog_info.product, "Verilator") != nullptr);
    if (g_is_verilator) {
        vpi_printf("** Info: Verilator VPI: discovering instance nets via vpiReg\n");
        g_interface->set_always_put_outputs(true);
    }

    // Process each HDL instance
    for (const std::string& instance_name : g_config.hdl_instance_names) {
        vpiHandle inst = find_hdl_instance(instance_name);
        if (inst == nullptr) {
            ERROR("ERROR: instance \"%s\" not found", instance_name.c_str());
            continue; // Continue with other instances instead of returning
        }

        vpi_printf("** Info: Processing instance: %s\n", instance_name.c_str());

        // Verilator does not implement vpi_iterate(vpiPort). Use vpiReg there.
        vpiHandle iter = g_is_verilator ? vpi_iterate(vpiReg, inst) : vpi_iterate(vpiPort, inst);
        if (iter == nullptr) {
            ERROR("ERROR: cannot iterate ports/regs on instance \"%s\"", instance_name.c_str());
            continue;
        }

        vpiHandle port = nullptr;
        while ((port = vpi_scan(iter)) != nullptr) {

            const char *pname_c = vpi_get_str(vpiName, port);
            std::string pname = pname_c != nullptr ? pname_c : "";
            int dir = vpi_get(vpiDirection, port);

            if (dir == vpiInout) {
                ERROR(" port %s inout - not supported", pname.c_str());
                continue;
            }
            if (dir != vpiInput && dir != vpiOutput) {
                const int obj_type = vpi_get(vpiType, port);
                vpiHandle net = port;
                if (obj_type == vpiPort) {
                    vpiHandle module = vpi_handle(vpiParent, port);
                    net = vpi_handle_by_name(const_cast<char *>(pname.c_str()), module);
                }
                if (net != nullptr) {
                    dir = vpi_get(vpiDirection, net);
                }
            }
            if (dir != vpiInput && dir != vpiOutput) {
                INFO("skip %s: no input/output direction (dir=%d)", pname.c_str(), dir);
                continue;
            }

            vpiHandle alias = g_interface->add_port(port, instance_name);

            const int obj_type = vpi_get(vpiType, port);
            vpiHandle net = port;
            if (obj_type == vpiPort) {
                vpiHandle module = vpi_handle(vpiParent, port);
                net = vpi_handle_by_name(const_cast<char*>(pname.c_str()), module);
            }
            if (dir == vpiInput && net != nullptr) {
                // Verilator's cbValueChange scanner fatals on VLVT_REAL
                // ("Unsupported type (8)"). Poll reals in the timestep instead.
                const int net_type = vpi_get(vpiType, net);
                auto register_vc = [](vpiHandle obj) {
                    s_cb_data cb_data_s{};
                    cb_data_s.reason = cbValueChange;
                    cb_data_s.cb_rtn = vpi_port_change_cb;
                    cb_data_s.obj = obj;
                    cb_data_s.time = nullptr;
                    cb_data_s.value = nullptr;
                    vpi_register_cb(&cb_data_s);
                };
                if (g_is_verilator && net_type == vpiRealVar) {
                    DBG("skip cbValueChange on real %s (Verilator)", pname.c_str());
                } else {
                    register_vc(net);
                    if (alias != nullptr && alias != net) {
                        const int alias_type = vpi_get(vpiType, alias);
                        if (!(g_is_verilator && alias_type == vpiRealVar)) {
                            register_vc(alias);
                        }
                    }
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

    if (g_is_verilator) {
        schedule_vpi_cb(cbReadWriteSynch, 0, spice_vpi::vpi_timestep_cb);
    }
    // Delay 1 so Verilator places this on the future queue (--binary has no
    // cocotb loop to drain a 0-delay AfterDelay sitting on the current list).
    next_time_cb_handle = schedule_timestep_cb(1);

    return 0;
}

auto vpi_end_of_sim_cb(p_cb_data cb_data_p) -> PLI_INT32 {

    g_time_barrier.shutdown();

    ngSpice_Command((char *)"bg_halt");
    // A full transient dump can be hundreds of megabytes for co-simulation.
    // Keep it opt-in so ending a test does not block while writing dump.raw.
    if (std::getenv("SPICE_DUMP_RAW") != nullptr) {
        // ngSpice_Command((char *)"set filetype=ascii");
        ngSpice_Command((char *)"write dump.raw");
    }

    vpi_printf("End of simulation\n");

    return 0;
}

} // namespace spice_vpi 
