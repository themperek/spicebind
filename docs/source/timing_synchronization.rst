Timing Synchronization Between NGSPICE and VPI
===============================================

Overview
--------

This document explains the timing synchronization mechanism used in SpiceBind to coordinate simulation time between the digital HDL simulator (via VPI) and the analog SPICE simulator (NGSPICE). This mechanism ensures that both simulators advance in lock-step and can handle feedback between digital and analog domains.

Key Components
--------------

1. Time Barrier (``TimeBarrier.h``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``TimeBarrier`` class is the core synchronization primitive that coordinates time progression between two simulation engines:

- **HDL_ENGINE_ID (0)**: Digital HDL simulator
- **SPICE_ENGINE_ID (1)**: NGSPICE analog simulator

The barrier ensures that neither simulator advances too far ahead of the other, maintaining synchronization.

2. Global State Variables
^^^^^^^^^^^^^^^^^^^^^^^^^

- ``g_time_barrier``: Global instance of ``TimeBarrier<unsigned long long>``
- ``add_ngspice_timestep``: Flag indicating if NGSPICE needs a new timestep

Timing Synchronization Flow
---------------------------

The timing synchronization follows a specific sequence when digital inputs to SPICE change:

Step 1: Digital Signal Change Detection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Function**: ``vpi_port_change_cb`` (``VpiCallbacks.cpp``)

.. code-block:: cpp

   auto vpi_port_change_cb(p_cb_data cb_data_p) -> PLI_INT32

- **Trigger**: ``cbValueChange`` callback registered for every input port from VPI to SPICE
- **Purpose**: Detects when a digital signal changes that affects SPICE simulation
- **Key Actions**:
  
  - Removes existing next time callbacks to prevent conflicts
  - Sets ``add_ngspice_timestep = true`` (only once per time step if multiple signals change)
  - Registers immediate ``cbAfterDelay`` callback with delay = 0

Step 2: Immediate Timestep Callback
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Function**: ``vpi_timestep_cb`` (``VpiCallbacks.cpp``)

.. code-block:: cpp

   auto vpi_timestep_cb(p_cb_data cb_data_p) -> PLI_INT32

- **Trigger**: ``cbAfterDelay`` with delay = 0, registered by ``vpi_port_change_cb``
- **Purpose**: Adds a new timestep to NGSPICE and coordinates synchronization

**Key Actions**:

1. **Add NGSPICE Timestep** (if ``add_ngspice_timestep == true``):
   
   .. code-block:: cpp
   
      g_time_barrier.update_no_wait(SPICE_ENGINE_ID, current_time);
      g_time_barrier.set_needs_redo(true);
   
   - Informs NGSPICE to add a timestep at the current VPI time
   - Sets redo flag to signal NGSPICE needs to recalculate

2. **Update VPI Time**:
   
   .. code-block:: cpp
   
      g_time_barrier.update(HDL_ENGINE_ID, current_time + 1);
   
   - Updates HDL engine time and waits for NGSPICE synchronization

3. **Update Digital Inputs**:
   
   .. code-block:: cpp
   
      g_interface->update_all_digital_inputs();
   
   - Applies new digital input values to SPICE simulation

4. **Update Digital Outputs**:
   
   .. code-block:: cpp
   
      g_interface->set_digital_output();
   
   - Propagates analog results back to digital domain

Step 3: NGSPICE Synchronization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Function**: ``ng_sync`` (``NgSpiceCallbacks.cpp#L18``)

.. code-block:: cpp

   int ng_sync(double actual_time, double *delta_time, double old_delta_time, 
              int redostep, int identification_number, int location, void *user_data)

- **Trigger**: Called by NGSPICE at each simulation step
- **Location**: NgSpiceCallbacks.cpp:18
- **Purpose**: Handles redo operations and synchronizes NGSPICE with VPI timing

**Key Behaviors**:

1. **Redo Handling** (when ``location == 1`` and ``needs_redo() == true``):
   
   - Calculates new delta time to backtrack to the VPI-requested time
   - Returns ``1`` to signal NGSPICE to redo the current step
   - Resets ``needs_redo`` flag

2. **End Step Processing** (when ``location == 0``):
   
   - Updates next SPICE step time
   - Calls ``analog_outputs_update()`` to read analog results

Step 4: NGSPICE Data Source Callback
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Function**: ``ng_srcdata`` (``NgSpiceCallbacks.cpp``)

.. code-block:: cpp

   int ng_srcdata(double *vp, double time, char *source, int id, void *udp)

- **Trigger**: Called by NGSPICE to get input signal values
- **Purpose**: Provides current digital input values to NGSPICE

**Key Actions**:

- Updates SPICE engine time (if not in redo mode) for next event -> will create next ``cbAfterDelay``
- Sets analog input values from digital signals via ``g_interface->set_analog_input()``

Step 5: Wait for Timestep Completion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Function**: ``vpi_timestep_cb`` (``VpiCallbacks.cpp``) (continued)

After initiating the NGSPICE timestep:

- The VPI timestep callback waits for NGSPICE to complete the step
- Uses ``g_time_barrier.update()`` which blocks until both engines are synchronized
- Once synchronized, schedules the next timestep callback

Time Barrier Synchronization Details
-------------------------------------

The ``TimeBarrier`` class provides several synchronization methods:

``update(engine_id, current_time)``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Updates time for one engine and **waits** for the other engine to catch up
- Blocks calling thread until synchronization is achieved

``update_no_wait(engine_id, current_time)``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Updates time for one engine **without waiting**
- Used to set SPICE timesteps without blocking VPI

``set_needs_redo(bool)`` / ``needs_redo()``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Signals when NGSPICE needs to redo a simulation step
- Used when VPI changes require NGSPICE to backtrack in time

``set_next_spice_step_time(time)`` / ``get_next_spice_step_time()``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Manages the next scheduled NGSPICE timestep
- Ensures VPI callbacks are scheduled at the correct times

Timing Diagram
--------------

::

   VPI Time    : |----1----2----3----4----5--->
                 |    ^         ^
                 |    |         |
   SPICE Time    : |----1----2----3----4----5--->
                 |         ^    ^
                 |         |    |
   Actions       : Port     |    Wait for
                   Change   |    completion
                            |
                       Add timestep +
                       Signal redo

Key Design Principles
---------------------

1. **Event-Driven**: Changes in digital signals trigger synchronization
2. **Lock-Step Execution**: Neither simulator advances too far ahead
3. **Redo Capability**: NGSPICE can backtrack when VPI signals change 