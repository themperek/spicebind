---
marp: true
theme: default
size: 16:9
paginate: true
header: '![](../../assets/spicebind_logo.svg)'
footer: '<span class="foot-left">OrConf 2026</span><a class="foot-center" href="https://fossi-foundation.org/orconf/2026#spicebind-bringing-spice-into-rtl-verification">SpiceBind: Bringing SPICE into RTL Verification</a><span class="foot-right">Tomasz Hemperek <a href="mailto:mail@themperek.com">mail@themperek.com</a></span>'
style: |
  :root {
      --spicebind-bg: #FCFCFB;
      --spicebind-text: #202326;
      --spicebind-muted: #626970;
      --spicebind-line: #D9DEE2;
      --spicebind-accent: #147D92;
      --spicebind-soft: #A8D3DE;
      --spicebind-red: #B43832;
    }

  section {
      width: 1280px;
      height: 720px;
      display: flex;
      gap: 20px;
      flex-direction: column;
      justify-content: flex-start;
      padding: 52px 78px 86px 78px;
      background-color: var(--spicebind-bg);
      color: var(--spicebind-text);
      font-family: Aptos, Inter, 'Helvetica Neue', Arial, sans-serif;
      font-size: 28px;
      letter-spacing: -0.01em;
    }

  section > * {
      position: relative;
      z-index: 1;
    }

  section > header,
  section > footer {
      position: absolute;
    }

  h1 {
      margin: 0 180px 10px 0;
      padding: 0;
      color: var(--spicebind-text);
      font-size: 44px;
      font-weight: 650;
      line-height: 1.08;
      letter-spacing: -0.035em;
    }

  h2 {
      margin: 0 0 18px 0;
      color: var(--spicebind-text);
      font-size: 31px;
      font-weight: 600;
      line-height: 1.15;
      letter-spacing: -0.025em;
    }

  p, li {
      color: var(--spicebind-text);
      font-size: 20px;
      line-height: 1.34;
    }

  ul {
      margin-top: 0;
      padding-left: 1.05em;
    }

  li + li {
      margin-top: 0.28em;
    }

  strong {
      color: var(--spicebind-accent);
      font-weight: 650;
    }

  code {
      background: rgba(20, 125, 146, 0.08);
      color: #145A68;
      border-radius: 0.22em;
      padding: 0.05em 0.22em;
      font-family: 'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace;
    }

  pre {
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(98, 105, 112, 0.16);
      border-radius: 14px;
      padding: 18px 22px;
      box-shadow: 0 8px 30px rgba(32, 35, 38, 0.045);
    }

  pre code {
      background: transparent;
      color: var(--spicebind-text);
      padding: 0;
      font-size: 19px;
      line-height: 1.33;
    }

  a {
      color: var(--spicebind-accent);
      text-decoration: none;
    }

  blockquote {
      margin: 0;
      padding-left: 22px;
      border-left: 4px solid var(--spicebind-accent);
      color: var(--spicebind-muted);
    }

  section > header {
      position: absolute !important;
      top: 28px !important;
      right: 40px !important;
      left: auto !important;
      width: auto !important;
      height: auto !important;
      overflow: visible !important;
      padding: 0 !important;
      line-height: 0;
      z-index: 4;
    }

  header p {
      margin: 0;
      overflow: visible;
      line-height: 0;
    }

  header img {
      display: block;
      height: 56px !important;
      width: auto !important;
      max-width: none !important;
    }

  footer {
      left: 78px;
      right: 78px;
      bottom: 18px;
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      height: 24px;
      padding-top: 8px;
      border-top: 1px solid rgba(98, 105, 112, 0.18);
      color: var(--spicebind-muted);
      font-size: 13px;
      white-space: nowrap;
      letter-spacing: 0;
      z-index: 3;
      pointer-events: auto;
    }

  footer p {
      display: contents;
    }

  footer .foot-left {
      justify-self: start;
    }

  footer .foot-center {
      justify-self: center;
      text-align: center;
    }

  footer .foot-right {
      justify-self: end;
      text-align: right;
    }

  footer a {
      color: var(--spicebind-accent);
      text-decoration: none;
    }

  section::after {
      position: absolute;
      right: 26px;
      bottom: 20px;
      font-size: 13px;
      color: var(--spicebind-muted);
      font-variant-numeric: tabular-nums;
      z-index: 3;
    }

  section.lead::after {
      display: none;
    }

  section.lead {
      justify-content: center;
      align-items: center;
      text-align: center;
      padding: 86px 78px;
    }

  section.lead h1 {
      max-width: 900px;
      margin: 0 auto 22px auto;
      font-size: 58px;
      line-height: 1.02;
      text-align: center;
    }

  section.lead p {
      max-width: 780px;
      margin: 0 auto;
      color: var(--spicebind-muted);
      font-size: 28px;
      text-align: center;
    }

  section.section {
      justify-content: flex-start;
    }

  section.section h1 {
      max-width: 920px;
      font-size: 54px;
      margin-bottom: 12px;
    }

  section.section p {
      max-width: 740px;
      color: var(--spicebind-muted);
      font-size: 27px;
    }

  .two-col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      align-items: start;
    }

  .two-col.w2-1 {
      grid-template-columns: 2fr 1fr;
    }

  .two-col.w1p7-1 {
      grid-template-columns: 1.7fr 1fr;
    }


  .two-col.center-2 {
      width: 68%;
      margin: 0 auto;
    }

  .muted {
      color: var(--spicebind-muted);
    }

  .small {
      font-size: 20px;
      color: var(--spicebind-muted);
    }

  .card {
      border: 1px solid rgba(98, 105, 112, 0.18);
      border-radius: 0px;
      font-size: 20px;
      background: #ffffff;
      padding: 10px 10px;
    }
    .card h2 {
      margin: 0 0 8px 0;
      font-size: 25px;
      line-height: 1.12;
    }
    .card p {
      margin: 0;
      font-size: 18px;
      line-height: 1.28;
    }
    .card-failure {
      border-color: rgba(198, 58, 58, 0.45);
      background: linear-gradient(180deg, #fff, #fff7f5);
    }
    .card-failure h2 {
      color: var(--spicebind-red);
    }
    .card-footer {
      margin-top: auto;
      padding-top: 10px;
      border-top: 1px solid rgba(98,105,112,0.16);
      font-size: 18px;
      line-height: 1.25;
      color: var(--spicebind-muted);
    }

  .side {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  
  .flow-table {
     font-size: 18px;
  }

  .flow-table table {
     width: 100%;
     border-collapse: collapse;
  }
  .flow-table th, .flow-table td {
     border: 1px solid rgba(98, 105, 112, 0.20);
     padding: 8px 10px;
     vertical-align: middle;
  }
  .flow-table th {
     background: rgba(98, 105, 112, 0.06);
     font-weight: 650;
  }
  .flow-table tr.focus td {
     background: rgba(20, 125, 146, 0.08);
  }

  .arch {
      display: flex;
      align-items: stretch;
      gap: 10px;
      margin: 0 0 18px 0;
    }
  .arch-group {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 8px;
      min-width: 0;
    }
  .arch-group-hdl {
      flex: 2.1;
    }
  .arch-group-body {
      display: flex;
      align-items: stretch;
      gap: 8px;
      flex: 1;
    }
  .arch-kicker {
      font-size: 13px;
      font-weight: 650;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--spicebind-muted);
      text-align: center;
    }
  .arch-box {
      flex: 1;
      border: 1px solid rgba(98, 105, 112, 0.18);
      border-radius: 0px;
      background: #fff;
      padding: 16px 10px;
      text-align: center;
      font-size: 18px;
      font-weight: 650;
      line-height: 1.2;
    }
  .arch-box span {
      display: block;
      margin-top: 5px;
      font-size: 14px;
      font-weight: 400;
      color: var(--spicebind-muted);
    }
  .arch-sb {
      border-color: rgba(20, 125, 146, 0.45);
      background: linear-gradient(180deg, #fff, #eaf7f4);
      color: var(--spicebind-accent);
    }
  .arch-arrow {
      align-self: center;
      flex: 0 0 auto;
      color: var(--spicebind-muted);
      font-size: 22px;
    }
  .three-col {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 16px;
      align-items: start;
    }
  .runtime {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 4px;
    }
  .runtime-row {
      display: grid;
      grid-template-columns: 140px 1fr 72px;
      gap: 10px;
      align-items: center;
      font-size: 16px;
    }
  .runtime-bar {
      height: 14px;
      border-radius: 7px;
      background: var(--spicebind-line);
    }
  .runtime-bar.beh {
      width: 4%;
      background: #9aa3aa;
    }
  .runtime-bar.spice {
      width: 100%;
      background: var(--spicebind-accent);
    }
  .leadline {
      margin: 0 0 14px 0;
      font-size: 22px;
      color: var(--spicebind-muted);
    }

  .benefit-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      align-items: stretch;
    }
  .benefit-grid .card {
      padding: 18px 18px;
    }
  .benefit-grid .card h2 {
      font-size: 28px;
      margin-bottom: 10px;
    }
  .benefit-grid .card p {
      font-size: 20px;
      line-height: 1.30;
    }
  .caption {
      margin-top: 6px;
      color: var(--spicebind-text);
      font-weight: 650;
      font-size: 20px;
      line-height: 1.20;
      text-align: center;
    }
  .support {
      color: var(--spicebind-muted);
      font-size: 18px;
      line-height: 1.25;
      text-align: center;
    }

  .closing-hero {
      margin-top: 6px;
      font-size: 40px;
      line-height: 1.08;
      font-weight: 760;
      letter-spacing: -0.035em;
      color: var(--spicebind-accent);
    }
  .closing-sub {
      margin-top: 10px;
      max-width: 920px;
      font-size: 24px;
      line-height: 1.25;
      color: var(--spicebind-text);
    }
  .closing-grid {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 16px;
      margin-top: 20px;
    }
  .closing-card {
      border: 1px solid rgba(98, 105, 112, 0.18);
      border-radius: 0px;
      background: #fff;
      padding: 16px 18px;
    }
  .closing-card h2 {
      margin: 0 0 10px 0;
      font-size: 26px;
      line-height: 1.1;
    }
  .closing-card p,
  .closing-card li {
      font-size: 18px;
      line-height: 1.28;
    }
  .closing-card ul {
      margin: 0;
      padding-left: 1.1em;
    }
  .closing-bottom {
      display: grid;
      grid-template-columns: 1.35fr 1fr;
      gap: 22px;
      align-items: end;
      margin-top: 28px;
    }
  .repo-big {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 38px;
      line-height: 1.05;
      font-weight: 760;
      letter-spacing: -0.03em;
      color: var(--spicebind-text);
    }
  .repo-big img {
      height: 34px;
      width: auto;
    }
  .support-box {
      text-align: center;
      color: var(--spicebind-muted);
      font-size: 17px;
      line-height: 1.25;
    }
  .support-box img {
      margin-top: 10px;
      max-width: 250px;
      height: auto;
    }
  .red {
      color: var(--spicebind-red);
      font-size: 30px;
    }
---

<!-- _class: lead -->
<!-- _paginate: false -->

# SpiceBind: Bringing SPICE into RTL Verification

<br>
Tomasz Hemperek

---

# ABC130: A strip readout ASIC for CERN

<div class="two-col">
<div>

<center><img src="figures/ABC130.png" height="380"></center>

<sup>[Source: ACES 2014](https://indico.cern.ch/event/287628/contributions/1640935)</sup>

</div>
<div>

<center><img src="figures/ABC130_block_diagram.png" height="200"></center>

<sup>[Source: CERN CDS](https://cds.cern.ch/record/1494098)</sup>

  <div class="card">
  <ul>
    <li>Large mixed-signal ASIC for ATLAS at LHC</li>
    <li>256-channel analog front-end + substantial digital logic</li>
    <li>Extensive design reviews and verification</li>
  </ul>
  </div>

</div>



</div>

<div class="card">
<center><b><div class="red"> First silicon: no data on output </div></b></center>
</div>

---

# What went wrong?

<div class="two-col w1p7-1">
<div class="side">

  <div class="card">
    <img src="figures/abc130_mixed_signal_issue.svg">
  </div>

</div>

<div class="side">

  <div class="card">
    <h2>Failure symptom</h2>
    <p><strong>No data output.</strong> The custom SLVS transceiver and its functional Verilog model disagreed on the polarity/meaning of the direction signal.</p>
  </div>

  <div class="card">
    <h2>Extensively verified chip</h2>
    <p>The chip had been extensively verified. The remaining gap was a <strong>mismatch between the functional model and the actual circuit.</strong>.</p>
  </div>

</div>
</div>

<div class="card">
  <h2>How do we catch this class of bug?</h2>

- Verify across the abstraction boundary, not only inside each domain.
- Exercise the actual custom circuit from the existing digital testbench.
- <strong>Replace only the blocks that need circuit-level accuracy.</strong>
</div>


---

# Digital vs. analog simulation

<div class="two-col">
<div class="side">

  <div class="card">
    <h2>Digital</h2>
    <center><img src="figures/digital_event_driven.svg" height="215"></center>
  </div>

- Discrete logic states (0, 1, X, Z)
- Event-driven — advance to the next event
- Scales to large systems and long simulations

</div>

<div class="side">

  <div class="card">
    <h2>Analog / SPICE</h2>
    <center><img src="figures/analog_quasi_continuous.svg" height="215"></center>
  </div>

- Continuous-valued voltages and currents
- Adaptive timesteps + nonlinear circuit solves
- Device-level fidelity, but computationally expensive

</div>
</div>

<div class="card">
<center><strong>The problem:</strong> <b>mixed-signal designs need both. Behavioral models make system simulation practical, but they can disagree with the actual circuit.</b></center>
</div>

--- 

# Open-source mixed-signal approaches

<div class="flow-table">
<table>
  <colgroup>
    <col><col><col><col>
  </colgroup>
  <thead>
    <tr>
      <th>Approach</th>
      <th>Top level</th>
      <th>Digital execution</th>
      <th>Main characteristic</th>
    </tr>
  </thead>
  <tbody>
    <tr class="focus">
      <td><strong>SpiceBind</strong></td>
      <td>HDL simulator</td>
      <td>Normal HDL simulation</td>
      <td>Selected HDL instances are replaced by SPICE.</td>
    </tr>
    <tr>
      <td>ngspice <code>d_cosim</code></td>
      <td>ngspice / XSPICE</td>
      <td>HDL compiled as an XSPICE model</td>
      <td>SPICE-first flow: HDL blocks live inside ngspice.</td>
    </tr>
    <tr>
      <td>Yosys → XSPICE</td>
      <td>ngspice / XSPICE</td>
      <td>RTL mapped to gates and storage elements</td>
      <td>Single runtime simulator; digital behavior is synthesized logic.</td>
    </tr>
    <tr>
      <td><a href="https://github.com/VLSIDA/cocotbext-ams">cocotbext-ams</a></td>
      <td>cocotb / Python</td>
      <td>Normal HDL simulator</td>
      <td>Python coordinates HDL and analog simulators such as ngspice or Xyce.</td>
    </tr>
  </tbody>
</table>
</div>

<div class="card">
<center><strong>SpiceBind is HDL-first: </strong>keep the digital verification environment and use circuit-level simulation only for selected blocks.</center>
</div>

<div class="flow-table">
* Commercial Verilog-AMS and real-number-modeling flows cover broader use cases; not compared here.
</div>

--- 

# SpiceBind

<p class="leadline">Keep digital simulator as the top level. Attach ngspice only to the blocks that need a real circuit.</p>

<br>

<div class="arch">
  <div class="arch-group arch-group-hdl">
    <div class="arch-kicker">Existing HDL flow</div>
    <div class="arch-group-body">
      <div class="arch-box">Testbench<span>cocotb / Verilog</span></div>
      <div class="arch-arrow">↔</div>
      <div class="arch-box">HDL simulator<span>RTL + empty analog shells</span></div>
    </div>
  </div>
  <div class="arch-arrow">↔</div>
  <div class="arch-group">
    <div class="arch-kicker">VPI plugin</div>
    <div class="arch-box arch-sb">SpiceBind<span>A/D · D/A · time sync</span></div>
  </div>
  <div class="arch-arrow">↔</div>
  <div class="arch-group">
    <div class="arch-kicker">Circuit</div>
    <div class="arch-box">ngspice<span>selected instances only</span></div>
  </div>
</div>

<div class="three-col">
  <div class="card">
  <h2>Empty module</h2>
  <p>The analog block is a Verilog shell. SpiceBind binds the instance; the netlist is the implementation.</p>
  </div>

  <div class="card">
  <h2>Ports by name</h2>
  <p>HDL inputs drive <code>Vname … external</code>. Outputs come back from <code>v(name)</code>. Names match after lowercasing.</p>
  </div>

  <div class="card">
  <h2>One timeline</h2>
  <p>If an HDL event lands inside a SPICE step, that step is redone.</p>
  </div>
</div>


--- 

# Where SpiceBind helps

<br>

<div class="benefit-grid">
<div class="card">
<h2>Existing HDL flow</h2>
<p>Keep RTL, testbench, cocotb, waveform flow, and regressions where they already are.</p>
</div>
<div class="card">
<h2>SPICE only where it matters</h2>
<p>Run SPICE only for the instances where circuit behavior affects the system result.</p>
</div>
<div class="card">
<h2>Real mixed-signal checks</h2>
<p>Write tests and sweeps around ADCs, PLLs, DCOs, sensor front-ends, bias loops, and custom I/O.</p>
</div>
<div class="card">
<h2>Open-source stack</h2>
<p>Icarus Verilog, Verilator, ngspice, cocotb. Standard VPI, BSD-3-Clause. No vendor AMS simulator required.</p>
</div>
</div>

---

# Example: DCO calibration

<div class="card">
<center>
<div class="caption">Digitally controlled oscillator: 5-stage ring oscillator + binary-weighted switched load</div>
<img src="figures/spicebind_dco_concept.svg" width="900"><br>
</center>
</div>

<div class="flow-table">
<center>
<p><b>Analog oscillation simulation for nominal and fast corners</b></p>
<img src="figures/serv_dco_osc.png" width="900"><br>
</center>
</div>

---

# Same RTL system, one replaceable block

<div class="two-col w2-1">
<div class="side">

  <div class="card">
    <img src="figures/serv_dco_top_structure.svg">
  </div>

</div>

<div class="side">

  <div class="card">
    <h2>Same digital system</h2>
    <p>SERV CPU, RAM, Wishbone, and measurement logic remain normal RTL. The firmware runs unchanged.</p>
  </div>

  <div class="card">
    <h2>One replaceable block</h2>
    <p><code>dco_core</code> keeps the same HDL interface: <code>enable</code>, <code>trim[3:0]</code>, <code>osc</code>. Use the behavioral model for fast runs or bind the SPICE circuit with SpiceBind.</p>
  </div>

</div>
</div>

<div class="card">
<center><strong>Firmware, RTL and testbench stay unchanged.</strong> <b>Only the Digitally Controlled Oscillator implementation is replaced.</b></center>
</div>

---

# Firmware calibrates the circuit across corners

<div class="two-col">
<div>

<b>Firmware calibration loop</b>

<center>
<img src="figures/serv_dco_calibration_firmware.svg" height="415">
</center>
</div>
<div>

<b>Results before and after trimming across corners</b>

<center>
<img src="figures/serv_dco_trims.png" height="300" alt="Trim chosen by firmware">
</center>

<div class="card">
<div class="runtime">
<div class="runtime-row"><span>Behavioral</span><div class="runtime-bar beh"></div><span>~1 s</span></div>
<div class="runtime-row"><span>SPICE</span><div class="runtime-bar spice"></div><span>~50 s</span></div>
</div>
</div>

<div class="flow-table">
* Generic BSIM3 demo models, not a foundry PDK; extracted PDK netlists can be significantly slower.
</div>

</div>
</div>

---

# SpiceBind: practical mixed-signal verification

<!-- <div class="closing-hero">Put real circuits into your existing HDL tests.</div> -->

SpiceBind adds circuit-level simulation to selected blocks in an otherwise normal RTL verification flow.


<div class="closing-grid">
<div class="closing-card">
<h2>Fits the existing RTL flow</h2>
<ul>
<li>Keep the RTL simulator as top level.</li>
<li>Use an empty Verilog shell.</li>
<li>Bind one instance to an ngspice.</li>
</ul>
</div>

<div class="closing-card">
<h2>Circuit-level checks in context</h2>
<ul>
<li>Use the existing digital verification environment.</li>
<li>Compare behavioral and SPICE implementations.</li>
<li>Exercise the circuit together with RTL and firmware.</li>
</ul>
</div>

<div class="closing-card">
<h2>Save engineering time and reduce respin risk</h2>
<ul>
<li>Catch model/circuit mismatches before silicon.</li>
<li>Debug mixed-signal behavior in regression.</li>
<li>Spend SPICE only where it matters.</li>
</ul>
</div>
</div>

<center> <strong>Early release — feedback and contributions welcome </strong></center>

<div class="closing-bottom">
<div>

<a href="https://github.com/themperek/spicebind" class="repo-big">
  <img src="figures/github.svg"> themperek/spicebind
</a>
<p> </p>
<a href="https://www.linkedin.com/in/hemperek/">
  <img src="figures/LinkedIn.svg" height="20">
  linkedin.com/in/hemperek
</a>

</div>

<div class="support-box">
Thanks for support to<br>
<a href="https://dectris.com/"><img src="figures/DECTRIS_logo.svg"></a>
</div>
</div>

