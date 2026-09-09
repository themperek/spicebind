Timing synchronization between ngspice and VPI
===============================================

SpiceBind runs two simulators on one virtual clock: the HDL simulator
(Icarus or Verilator) on the VPI thread, and ngspice on a background
thread (``bg_run``). A digital event can land in the middle of an analog
step. The two sides wait for each other; this page is the mechanism,
including ngspice redo.

Two simulators, one time
------------------------

HDL time is an integer tick at the simulator precision. With
``timescale 1ns/1ps``, one tick is 1 ps. ngspice time is a floating-point
number of seconds. The VPI plugin converts with
``10**(-vpiTimePrecision)`` ticks per second.

They cannot free-run. If ngspice jumps 1 ns while HDL has an edge at
0.3 ns, the analog circuit sees the new digital value too late. If HDL
runs ahead, analog outputs on HDL nets are stale.

The plugin keeps both on the same timeline with
``TimeBarrier<unsigned long long>`` in ``cpp/TimeBarrier.h``. Engine 0 is
HDL, engine 1 is SPICE. ``update(engine, t)`` publishes ``t`` for that
engine and blocks until the other engine's time is at least ``t``.
``shutdown()`` wakes anyone still waiting (HDL end of sim, or ngspice
``ng_exit``).

The ``.tran`` line in the netlist is part of this contract. Stop time
must be longer than the HDL run, with a unit (``1m``, ``2us``). A bare
``.tran 1ns 1`` is a 1 ns step for one second, and ngspice tries to
allocate about 1e9 points (``malloc`` / exit -11). If ngspice
finishes ``.tran`` first, the barrier waits forever: the analog progress
bar sits at 100 %, then nothing.

The time barrier
----------------

On a quiet stretch, ngspice proposes the next analog time (often the
``.tran`` step). HDL schedules a VPI ``cbAfterDelay`` for that time.
When that callback fires, HDL calls ``update(HDL, now+1)``: it claims
"I am at now plus one precision tick" and waits until SPICE has reached
that. ngspice, when it needs an external source voltage, calls
``ng_srcdata``, which does ``update(SPICE, analog_time)`` and waits until
HDL has reached that analog time.

Each side waits for the other. The ``+1`` tick lets ngspice take a point
at the HDL event and then move a fraction of a picosecond past it so the
wait can complete.

When a digital input changes
----------------------------

``cbValueChange`` on each HDL-to-SPICE input runs
``vpi_port_change_cb`` (``cpp/VpiCallbacks.cpp``). Several ports can
change in the same slot; the timestep work is registered once.

The callback cancels the pending "next analog time" ``cbAfterDelay``,
because that time is no longer the plan. It then registers a 0-delay
timestep:

- Icarus: ``cbAfterDelay`` with delay 0, which still runs in this slot.
- Verilator: ``cbReadWriteSynch``. Verilator ``--main`` has already
  drained timed callbacks this cycle, so a 0-delay ``cbAfterDelay``
  would not run until time had already moved.

``vpi_timestep_cb`` then:

1. On Verilator, sample parent/TOP aliases. A cocotb write can land on
   those nets after the instance net that ``cbValueChange`` saw.
2. Copy HDL inputs into analog sources
   (``update_all_digital_inputs()``) before waiting.
3. ``request_spice_point(t)``: record that analog should land on this
   HDL time, and set ``needs_redo``.
4. ``update(HDL, t+1)`` and wait for ngspice.
5. Push analog-backed HDL outputs (``set_digital_output()`` /
   ``vpi_put_value``). Icarus does this in AfterDelay. Verilator
   schedules ``cbReadWriteSynch`` instead. A Verilator AfterDelay put
   makes delay-chain bits appear one sample early.
6. Schedule the next AfterDelay at the analog time ngspice just
   proposed (at least one tick ahead).

What ngspice means by redo
--------------------------

ngspice calls ``ng_sync`` from ``dctran.c`` ``sharedsync`` at two
places in each analog step, with a ``location`` argument:

Location 0 is after breakpoint handling, before XSPICE events and
the analog solve. Location 1 is after the analog solve.

The proposed step is ``actual_time`` plus ``*delta_time`` (seconds).
Returning 1 from ``ng_sync`` means: reject this analog time, keep
the circuit at the previous accepted point, and try again with a new
``delta``. That is a redo.

A redo at location 0 happens before XSPICE and analog evaluation, so
those engines never see the rejected time. A redo at location 1 happens
after they have already run. The analog delay model (below) has already
sampled the point. It does not rewind.

SpiceBind's ``ng_sync`` always returns 0. It never asks ngspice to
reject a point that was already solved. The ``needs_redo`` flag on the
barrier is a different thing: it means "HDL asked for a point inside the
step that is about to start; shrink ``delta`` at location 0."

How the analog step is shortened
--------------------------------

Suppose analog is at 2.00 ns and would like to go to 3.00 ns (``delta``
= 1 ns). HDL changes an input at 2.37 ns.

If analog ran all the way to 3.00 ns, XSPICE would see the new digital
value as if it had been true for the whole nanosecond. Delayed events
could fire too early.

At location 0, ``cut_step_to_hdl_request`` (``cpp/NgSpiceCallbacks.cpp``)
looks at the HDL request:

- If 2.37 ns is strictly inside (2.00, 3.00), it writes a smaller
  ``*delta_time`` so the next analog point is 2.37 ns, then clears
  ``needs_redo``.
- If the proposed point is already 2.37 ns, it leaves ``delta``
  alone. Rejecting a valid point would make ngspice evaluate that time
  twice.
- If the request is outside this step, it leaves ``delta`` alone.

Then ``ng_sync`` returns 0. ngspice takes a normal (shorter) step to
2.37 ns. No analog point is thrown away.

While that cut is in flight, ``needs_redo`` is true.
``ng_srcdata`` must not call the blocking ``update(SPICE, t)``.
HDL is already sitting in ``update(HDL, t+1)`` waiting for SPICE.
If SPICE also waits for HDL, both sides block forever.

Once location 0 has applied (or discarded) the cut, ``needs_redo`` is
false again and ``ng_srcdata`` goes back to waiting for HDL as usual.

``analog_outputs_update()`` also runs at location 0. It reads the latest
``ngGet_Vec_Info`` samples into a cache. HDL later copies that cache
onto nets with ``set_digital_output()``. Reading analog and putting HDL
values are two steps, not one.

Why the analog delay cannot rewind
----------------------------------

The delay in ``tests/test.cir`` and ``tests/timing_edges.cir`` is XSPICE
``delay`` (ngspice ``src/xspice/icm/analog/delay/cfunc.mod``,
``cm_delay``).

It samples when ``TIME >= step_count * TSTEP``, using the ``.tran``
step, not every solver time. The samples live in a private circular
buffer. If ngspice rejects a point, that buffer does not rewind.
``buff_del`` is updated after ``OUTPUT(out)``, so the delayed value
often shows up on the next analog evaluation. The model also adds
``0.5 * tstep`` into ``delay_step``.

If extra analog points cross a TSTEP, the buffer is sampled extra
times. The delay looks shorter or jumpy, especially when DAC and PWM
toggle at the same time as the delayed bits.

That is why SpiceBind does not return 1 from ``ng_sync`` at location 1:
the delay model would keep the extra sample. It is also why a 1 ns
``.tran`` step cannot resolve a 2 ns delay the way a 100 ps step can.
Production ``tests/test.cir`` stays ``.tran 1ns 1m``.
``tests/test_tb.py`` samples between edges (1.5 ns, 3.5 ns, ...).
Exact 2 ns, 4 ns, ... edges are on ``tests/timing_edges.cir``
(``.tran 100ps 2us``).

Writing analog results back to HDL
----------------------------------

The analog solve finishing and the HDL process reading ``adc_out`` are
not the same event.

Icarus puts analog-backed nets in AfterDelay, in the same region as
``#2``. Which one runs first is up to the simulator. A Verilog
``#2; x = adc_out`` can resume before the put, so ``x`` is still 0.

Verilator puts in ``cbReadWriteSynch``. Cocotb ``Timer`` often samples
after that work has run. ``Timer`` alone, ``ReadOnly``, and
``ReadWrite`` all see the delayed bit at the exact 2 ns edge on the
100 ps fixture. Verilog ``#2`` and ``#2; #0`` still do not.
``#2; #0.1`` waits one extra analog step (100 ps on that fixture) and
the bit is there.

``tests/test_timing_edges.py`` is the cocotb check (one pytest case per
cocotb test, because ``cm_delay`` buffers leak across tests in one
sim). ``tests/test_timing_hdl.py`` is Verilog/SystemVerilog without
cocotb. Conservative HDL benches wait ``#2; #0.1``. Plain ``#2`` is a
strict xfail until the put happens before the process resumes.

HDL ``timescale`` does not change the analog delay. VPI still
converts ticks from ``vpiTimePrecision``. Combinations are in
``test_timing_timescale``, using ``#1ns`` so a 2 ns delay stays 2 ns
when the module unit is 1 ps or 1 us. Verilator with 1 ns precision
still has the delayed bit clear at 3 ns; that bench waits until 5 ns.

TimeBarrier calls
-----------------

``update(engine_id, t)``
    Publish ``t`` and wait until the other engine is at least ``t``.

``update_no_wait(engine_id, t)``
    Publish ``t`` without waiting. HDL uses this so SPICE's "now" is
    visible before the cut request.

``request_spice_point(t)`` / ``get_hdl_request_time()``
    HDL asks for an analog point at ``t``. Sets ``needs_redo``.
    Location 0 consumes it.

``set_next_spice_step_time`` / ``get_next_spice_step_time``
    Next analog time, used to schedule the next HDL AfterDelay.

``set_needs_redo`` / ``needs_redo``
    Cut in flight. This is not "return 1 from ``ng_sync`` at location 1".

What does not work
------------------

Waiting at location 0 until HDL time is past the proposed analog time
deadlocks. ngspice often truncates a step (1 ps, 3 ps, 7 ps, 15 ps)
while HDL is waiting at 10 ps or 2 ns.

Waiting until analog "accepted" ``t+1``, then inserting a 1-tick analog
catchup, can hit exact 2 ns edges on the 100 ps fixture. The extra 1 ps
points extra-sample ``cm_delay`` on the production 1 ns TSTEP when DAC
and PWM are toggling. Without the catchup, that wait deadlocks against
``ng_srcdata``.

Forcing analog onto the TSTEP grid collapsed the delay or broke
``tests/test_debug.py`` (inverter Y2).

A location 1 redo after analog solve extra-samples ``cm_delay``. The
delay looks early or jumpy under DAC/PWM.

If the sim hangs or the delay is wrong
--------------------------------------

Rebuild the VPI after C++ edits:
``cmake --build build --target spicebind_vpi`` (verbose:
``spicebind_vpi_debug``).

Check that ``.tran`` stop exceeds HDL time and has a unit.

Exact delay edges belong on ``timing_edges.cir`` (100 ps), not
``test.cir`` (1 ns). Moving samples to 1.5 ns or 2.2 ns hides the bug
the test is for.

Hung after analog 100 %: ``.tran`` ended first, or a new wait deadlocks
with ``ng_srcdata``. Do not add a wait in ``ng_srcdata`` while
``needs_redo`` is true without changing the HDL side as well.

Verilator bits one sample early: analog put is in AfterDelay instead of
ReadWriteSynch.

Verilog ``#2`` still 0 while cocotb ``Timer`` sees 1: put vs process
resume, not a wrong analog delay.

Run::

   pytest tests/test_timing_edges.py tests/test_timing_hdl.py
   SIM=verilator pytest tests/test_timing_edges.py tests/test_timing_hdl.py
