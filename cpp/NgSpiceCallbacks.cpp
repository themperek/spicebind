#include "NgSpiceCallbacks.h"
#include "Debug.h"
#include "TimeBarrier.h"
#include "AnalogDigitalInterface.h"
#include "vpi_user.h"
#include <cmath>
#include <string>


// TODO:  Maybe add another step after redo with 1 unit time for fast pulses

// External global variables (defined in vpi_module.cpp)
extern spice_vpi::TimeBarrier<unsigned long long> g_time_barrier;
extern std::unique_ptr<spice_vpi::AnalogDigitalInterface> g_interface;
extern spice_vpi::Config::Settings g_config;

namespace spice_vpi {

int ng_sync(double actual_time, double *delta_time, double old_delta_time, int redostep, int identification_number, int location, void *user_data) {

    unsigned long long delta_time_spice = static_cast<unsigned long long>(std::llround(*delta_time * g_config.time_precision));
    unsigned long long time_spice = static_cast<unsigned long long>(std::llround(actual_time * g_config.time_precision));

    unsigned long long next_spice_time = g_time_barrier.get_next_spice_step_time();
    unsigned long long get_spice_engine_time = g_time_barrier.get_time(spice_vpi::TimeBarrier<unsigned long long>::SPICE_ENGINE_ID);
    DBG("time_spice=%lld next_spice_step=%lld  get_spice_engine_time=%lld actual_time=%g delta_time=%g delta_time_spice=%lld old_delta_time=%g redostep=%d identification_number=%d location=%d ", time_spice, next_spice_time, get_spice_engine_time, actual_time,
        *delta_time, delta_time_spice, old_delta_time, redostep, identification_number, location);

    if (redostep) {
        DBG("return ngspice redostep=%d", redostep);
        return 0;
    }

    auto next_time_spice = time_spice + delta_time_spice;
    if (get_spice_engine_time > next_time_spice) {
        DBG("return ngspice get_spice_engine_time=%lld > next_time_spice=%lld", get_spice_engine_time, next_time_spice);
        return 0;
    }

    // add new timestep -> redo
    if (location == 1 and g_time_barrier.needs_redo()) {

        // Skip redo since the actual step is before next time step
        if (time_spice < get_spice_engine_time) {
            DBG("return ngspice cancel redo time_spice=%lld < get_spice_engine_time=%lld", time_spice, get_spice_engine_time);
            return 0;
        }

        unsigned long long old_delta_time_spice = std::llround(old_delta_time * g_config.time_precision);
        unsigned long long new_delta_time_spice = old_delta_time_spice - (time_spice - get_spice_engine_time);

        double redo_time_db = ((double)get_spice_engine_time) * 1.0/g_config.time_precision;
        double new_delta_time = old_delta_time - (actual_time - redo_time_db);

        new_delta_time = std::max(new_delta_time, 1.0/g_config.time_precision);

        *delta_time = new_delta_time;

        g_time_barrier.set_needs_redo(false);
        DBG("REDO redo_time_db=%g new_delta_time=%g time_spice=%lld delta_time_spice=%lld new_delta_time_spice=%lld", redo_time_db, *delta_time, time_spice,
            delta_time_spice, new_delta_time_spice);

        return 1;
    }

    // end step
    if (location == 0) {

        DBG("set_next_spice_step_time");
        g_time_barrier.set_next_spice_step_time(time_spice + delta_time_spice);

        //
        // read/update analog outputs values
        //
        g_interface->analog_outputs_update();
    }

    return 0;
}

int ng_srcdata(double *vp, double time, char *source, int id, void *udp) {

    unsigned long long time_spice_to_vpi = std::llround(time * g_config.time_precision);

    unsigned long long time_spice_engine = g_time_barrier.get_time(spice_vpi::TimeBarrier<unsigned long long>::SPICE_ENGINE_ID);   
    DBG("enter source=%s vp=%g time_spice_engine=%lld time_spice=%lld redo_step=%d  time_spice_to_vpi=%lld", source, *vp, time_spice_engine, time_spice_to_vpi, g_time_barrier.needs_redo(), time_spice_to_vpi);

    if (!g_time_barrier.needs_redo()) {
        DBG("update time_spice_to_vpi=%lld time_spice_engine=%lld", time_spice_to_vpi, time_spice_engine);
        g_time_barrier.update(spice_vpi::TimeBarrier<unsigned long long>::SPICE_ENGINE_ID, time_spice_to_vpi);
    }

    //
    // set analog inputs values
    //
    std::string port_name(source);
    port_name = port_name.substr(1);
    g_interface->set_analog_input(port_name, vp);

    DBG("end source=%s time_spice_to_vpi=%lld time=%g vp=%g time_ns=%g", source, time_spice_to_vpi, time, *vp, time * 1e9);

    return 0;
}

int ng_printf(char *output, int ident, void *userdata) {
    vpi_printf("NGSPICE: %s\n", output);
    return 0;
}

int ng_exit(int status, bool immediate, bool quit, int id, void *data) { 
    return 0; 
}

} // namespace spice_vpi 