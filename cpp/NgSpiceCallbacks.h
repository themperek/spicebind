#ifndef NGSPICE_CALLBACKS_H
#define NGSPICE_CALLBACKS_H

namespace spice_vpi {

/**
 * @brief NGSPICE callback functions for communication with the SPICE simulator
 * 
 * These functions are called by NGSPICE during simulation to:
 * - Synchronize time steps between HDL and SPICE
 * - Exchange signal data between simulators
 * - Handle NGSPICE output and status
 */

/**
 * @brief NGSPICE synchronization callback
 * 
 * Called by NGSPICE at each simulation step to coordinate timing
 * and handle redo operations when HDL signals change.
 * 
 * @param actual_time Current SPICE simulation time
 * @param delta_time Pointer to next time step delta
 * @param old_delta_time Previous time step delta
 * @param redostep Redo step flag
 * @param identification_number Identification number
 * @param location Location indicator (0=end step, 1=begin step)
 * @param user_data User data pointer
 * @return 0 for normal operation, 1 for redo request
 */
int ng_sync(double actual_time, double *delta_time, double old_delta_time, 
           int redostep, int identification_number, int location, void *user_data);

/**
 * @brief NGSPICE source data callback
 * 
 * Called by NGSPICE to get input signal values from HDL simulator.
 * 
 * @param vp Pointer to voltage value to be set
 * @param time Current SPICE time
 * @param source Source name (signal name)
 * @param id Source identifier
 * @param udp User data pointer
 * @return 0 on success
 */
int ng_srcdata(double *vp, double time, char *source, int id, void *udp);

/**
 * @brief NGSPICE printf callback
 * 
 * Called by NGSPICE to output messages and status information.
 * 
 * @param output Output string from NGSPICE
 * @param ident Indentation level
 * @param userdata User data pointer
 * @return 0 on success
 */
int ng_printf(char *output, int ident, void *userdata);

/**
 * @brief NGSPICE exit callback
 * 
 * Called when NGSPICE simulation terminates.
 * 
 * @param status Exit status
 * @param immediate Immediate exit flag
 * @param quit Quit flag
 * @param id Process identifier
 * @param data User data pointer
 * @return 0 on success
 */
int ng_exit(int status, bool immediate, bool quit, int id, void *data);

} // namespace spice_vpi

#endif // NGSPICE_CALLBACKS_H 