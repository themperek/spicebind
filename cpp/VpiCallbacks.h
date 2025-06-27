#ifndef VPI_CALLBACKS_H
#define VPI_CALLBACKS_H

#include "vpi_user.h"

namespace spice_vpi {

/**
 * @brief VPI callback functions for HDL simulator integration
 * 
 * These functions are called by the VPI interface during HDL simulation to:
 * - Initialize and cleanup the SPICE bridge
 * - Handle signal changes and time synchronization
 * - Manage simulation flow between HDL and SPICE
 */

/**
 * @brief Start of simulation callback
 * 
 * Called when HDL simulation starts. Initializes NGSPICE, sets up ports,
 * and starts the co-simulation.
 * 
 * @param cb_data_p Callback data structure
 * @return 0 on success, non-zero on error
 */
PLI_INT32 vpi_start_of_sim_cb(p_cb_data cb_data_p);

/**
 * @brief End of simulation callback
 * 
 * Called when HDL simulation ends. Cleans up NGSPICE and saves results.
 * 
 * @param cb_data_p Callback data structure
 * @return 0 on success
 */
PLI_INT32 vpi_end_of_sim_cb(p_cb_data cb_data_p);

/**
 * @brief Timestep callback
 * 
 * Called at each HDL time step to synchronize with SPICE and
 * update signal values.
 * 
 * @param cb_data_p Callback data structure
 * @return 0 on success
 */
PLI_INT32 vpi_timestep_cb(p_cb_data cb_data_p);


/**
 * @brief Port change callback
 * 
 * Called when HDL signals change. Triggers synchronization
 * with SPICE simulator.
 * 
 * @param cb_data_p Callback data structure
 * @return 0 on success
 */
PLI_INT32 vpi_port_change_cb(p_cb_data cb_data_p);

/**
 * @brief Register VPI callbacks
 * 
 * Registers all necessary VPI callbacks with the HDL simulator.
 * This function is called during VPI initialization.
 */
void register_vpi_callbacks(void);

} // namespace spice_vpi

#endif // VPI_CALLBACKS_H 