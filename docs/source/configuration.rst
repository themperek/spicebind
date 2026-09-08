Runtime Configuration
=====================

SpiceBind reads its runtime configuration from environment variables.

``SPICE_NETLIST``
    Path to the ngspice netlist.

``HDL_INSTANCE``
    HDL instance path, or a comma-separated list of instance paths.

``VCC``
    Supply voltage used for digital-to-analog conversion. Defaults to ``1.0``.

``SPICE_DUMP_RAW``
    When set to any value, writes ngspice transient data to ``dump.raw`` when
    the simulation shuts down. This is disabled by default because
    co-simulation runs can produce very large raw files.

To enable the raw dump:

.. code-block:: console

   export SPICE_DUMP_RAW=1

HDL simulator
-------------

The test suite and examples select the HDL simulator with ``SIM``. The
default is ``icarus``. Set ``SIM=verilator`` for Verilator 5 (needs
``--timing`` and ``--vpi``). This variable is read by the Python runners,
not by the VPI plugin.
