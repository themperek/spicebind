#include "NgSpiceCallbacks.h"
#include "Debug.h"
#include "TimeBarrier.h"
#include "AnalogDigitalInterface.h"
#include "vpi_user.h"
#include <algorithm>
#include <cmath>
#include <string>


extern spice_vpi::TimeBarrier<unsigned long long> g_time_barrier;
extern std::unique_ptr<spice_vpi::AnalogDigitalInterface> g_interface;
extern spice_vpi::Config::Settings g_config;

namespace spice_vpi {

namespace {

auto min_spice_delta() -> double {
    return 1.0 / static_cast<double>(g_config.time_precision);
}

auto spice_ticks_to_seconds(unsigned long long ticks) -> double {
    return static_cast<double>(ticks) / static_cast<double>(g_config.time_precision);
}

void set_delta_ticks(double *delta_time, unsigned long long ticks) {
    *delta_time = std::max(spice_ticks_to_seconds(ticks), min_spice_delta());
}

// Cut a pending ngspice step before XSPICE processes its event queue. If the
// HDL changed an input inside the proposed step, letting XSPICE see the full
// step can make a delayed event appear before the HDL change occurred.
auto cut_step_to_hdl_request(double *delta_time, unsigned long long time_spice,
                             unsigned long long delta_time_spice) -> bool {
    if (!g_time_barrier.needs_redo()) {
        return false;
    }

    const unsigned long long request = g_time_barrier.get_hdl_request_time();
    if (time_spice >= request || time_spice + delta_time_spice < request) {
        return false;
    }
    if (time_spice + delta_time_spice == request) {
        // The proposed point already lands exactly on the HDL request; do
        // not make ngspice reject and repeat an otherwise valid point.
        g_time_barrier.set_needs_redo(false);
        g_time_barrier.set_next_spice_step_time(request);
        return false;
    }

    set_delta_ticks(delta_time, request - time_spice);
    g_time_barrier.set_needs_redo(false);
    g_time_barrier.set_next_spice_step_time(request);
    DBG("cut step to HDL request=%lld new_delta=%g", request, *delta_time);
    return true;
}

} // namespace

int ng_sync(double actual_time, double *delta_time, double old_delta_time, int redostep, int identification_number, int location, void *user_data) {

    unsigned long long delta_time_spice = static_cast<unsigned long long>(std::llround(*delta_time * g_config.time_precision));
    unsigned long long time_spice = static_cast<unsigned long long>(std::llround(actual_time * g_config.time_precision));

    unsigned long long next_spice_time = g_time_barrier.get_next_spice_step_time();
    unsigned long long spice_engine_time = g_time_barrier.get_time(spice_vpi::TimeBarrier<unsigned long long>::SPICE_ENGINE_ID);
    unsigned long long hdl_request = g_time_barrier.get_hdl_request_time();
    DBG("time_spice=%lld next_spice_step=%lld spice_engine=%lld hdl_request=%lld actual_time=%g delta_time=%g delta_time_spice=%lld old_delta_time=%g redostep=%d identification_number=%d location=%d ",
        time_spice, next_spice_time, spice_engine_time, hdl_request, actual_time,
        *delta_time, delta_time_spice, old_delta_time, redostep, identification_number, location);

    if (redostep) {
        DBG("return ngspice redostep=%d", redostep);
        return 0;
    }

    if (spice_engine_time > time_spice + delta_time_spice) {
        DBG("return ngspice spice_engine_time=%lld > next_time_spice=%lld",
            spice_engine_time, time_spice + delta_time_spice);
        return 0;
    }

    // Publish the accepted point and cut the upcoming step before XSPICE
    // processes events. Cutting after analog evaluation extra-samples cm_delay.
    if (location == 0) {
        if (g_time_barrier.needs_redo() && hdl_request <= time_spice) {
            g_time_barrier.set_needs_redo(false);
        }

        const unsigned long long proposed = time_spice + delta_time_spice;
        g_time_barrier.set_next_spice_step_time(proposed);
        g_interface->analog_outputs_update();
        cut_step_to_hdl_request(delta_time, time_spice, delta_time_spice);
        return 0;
    }

    // Location 1 redo rejects an analog point after cm_delay may already
    // have sampled it. The delay model does not rewind, so a redo shortens
    // (extra sample) or, with a later jump, lengthens the apparent delay.
    // Location 0 already cuts the next step to the HDL request.

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
    g_interface->set_analog_input(source + 1, vp);

    DBG("end source=%s time_spice_to_vpi=%lld time=%g vp=%g time_ns=%g", source, time_spice_to_vpi, time, *vp, time * 1e9);

    return 0;
}

int ng_printf(char *output, int ident, void *userdata) {
    vpi_printf("NGSPICE: %s\n", output);
    return 0;
}

int ng_exit(int status, bool immediate, bool quit, int id, void *data) {
    (void)status;
    (void)immediate;
    (void)quit;
    (void)id;
    (void)data;
    g_time_barrier.shutdown();
    return 0;
}

} // namespace spice_vpi
