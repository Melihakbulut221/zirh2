// =============================================================================
// ZIRH-2 - the SystemVerilog scenario suite
// test/sv/zirh_scenarios_tb.sv
//
// A self-checking, plusarg-driven scenario bench for the whole chip,
// written in the RTL's own language and runnable with nothing but
// iverilog -g2012. It complements the cocotb suites from a different
// angle: where cocotb tests one mechanism at a time, a scenario here is
// a MISSION SLICE - a sequence of abuse and normal operation woven
// together the way a bench day or a beam shift would produce it, with
// the pass criterion always the same: the chip keeps telling the truth
// on its pins.
//
//   make -C test -f Makefile.svs                # run every scenario
//   make -C test -f Makefile.svs SCENARIO=cmd_fuzz   # run one
//
// Scenarios (17):
//   boot_frame        first unprompted frame: sync, checksum, armed,
//                     counters zero
//   cpu_alive         CPU signature nonzero and changing across frames
//   echo_basic        0x41 comes back 0x42 through RX/bus/firmware/TX
//   echo_sweep        edge bytes echo, including the frame-sync
//                     colliding values 0x5A and 0x33
//   cmd_fuzz          junk command bytes never kill the computer
//   inject_counters   '1'/'4' land in exactly RAW_A/ESC_B; 'C' wipes
//   rom_checksum      'R' answers the committed mask's XOR fold
//   env_chain         'E' acks 'e', 'S' reads 1, 'B' reads 0
//   ifc_loopback      CAN beacon 'k'->'b', SpaceWire 'w'->'y', links
//                     looped in the bench topology
//   reset_midframe    reset in the middle of a telemetry frame; clean
//                     reboot to valid frames
//   reset_storm       five runt resets back to back; the chip still
//                     boots and reports
//   uart_glitch       a sub-bit runt low on RX frames no byte; a real
//                     byte right after still decodes
//   baud_drift        echo bytes sent at -5% and +5% bit period still
//                     decode (the RX oversampler's tolerance, proven)
//   uart_flood        back-to-back bytes at line rate; the computer
//                     survives and answers afterwards
//   tmr_flip_storm    forced single-replica upsets in live counters
//                     during traffic; voted state never wavers, frames
//                     keep their checksums
//   double_hit        the registered failure geometry: same bit, two
//                     replicas, one cycle - state corrupts, the chip
//                     survives and keeps framing
//   soak              a quiet stretch of frames: every checksum valid,
//                     every beam counter zero - the simulated
//                     false-positive floor
//
// House rules: no classes, no dynamic types - the full bench compiles
// under Icarus. Every check is an immediate assertion routed through
// check()/fatal bookkeeping so a failure names its scenario and dies
// loudly. Hierarchical force/release is confined to REPLICA outputs
// (u_ff_a/u_ff_b), the same discipline the cocotb flip helper proved:
// the voter output is the one place a fault must never be faked.
// =============================================================================

`default_nettype none
`timescale 1ns / 1ps

module zirh_scenarios_tb;

  // ---------------------------------------------------------------- constants
  localparam integer CLK_NS      = 40;       // 25 MHz
  localparam integer DIV         = 20;       // UART clocks per bit
  localparam integer BOOT_CYCLES = 120_000;
  localparam integer FRAME_LEN   = 20;
  localparam integer TLM_CYCLES  = (1 << 16) + 40_000;
  localparam [7:0]   ROM_SUM     = 8'hE5;

  // ------------------------------------------------------------------- wires
  reg         clk;
  reg         rst_n;
  reg         ena;
  reg  [7:0]  ui_in;
  reg  [7:0]  uio_in;
  wire [7:0]  uo_out;
  wire [7:0]  uio_out;
  wire [7:0]  uio_oe;

  // RESET_DIV=20 mirrors every cocotb suite. Stated HERE, on the
  // instance, because iverilog's -P reaches only root-scope modules
  // and the root here is the bench - a -P on the DUT is silently
  // ignored (measured: the chip kept talking at 174).
  tt_um_hma_zirh2 #(.RESET_DIV(20)) dut (
    .ui_in(ui_in), .uo_out(uo_out), .uio_in(uio_in), .uio_out(uio_out),
    .uio_oe(uio_oe), .ena(ena), .clk(clk), .rst_n(rst_n));

  wire uart_tx = uo_out[4];

  always #(CLK_NS / 2) clk = ~clk;

  // optional interface loopback (CAN_TX->CAN_RX, SPW_DOUT/SOUT->DIN/SIN)
  reg loop_en;
  always @(posedge clk)
    if (loop_en) begin
      uio_in[0] <= uio_out[1];   // CAN_TX  -> CAN_RX
      uio_in[2] <= uio_out[4];   // SPW_DOUT-> SPW_DIN
      uio_in[3] <= uio_out[5];   // SPW_SOUT-> SPW_SIN
    end

  // ------------------------------------------------------------- bookkeeping
  integer checks_done;
  integer scenarios_run;
  reg [8*24-1:0] cur_scn;

  task check(input cond, input [8*64-1:0] what);
    begin
      checks_done = checks_done + 1;
      if (!cond) begin
        $display("FAIL [%0s] %0s at %0t", cur_scn, what, $time);
        $fatal(1);
      end
    end
  endtask

  // ------------------------------------------------------------ UART driving
  task uart_bit(input b, input integer cycles);
    begin
      ui_in[3] = b;
      repeat (cycles) @(posedge clk);
    end
  endtask

  task uart_send(input [7:0] v);
    integer i;
    begin
      uart_bit(1'b0, DIV);
      for (i = 0; i < 8; i = i + 1) uart_bit(v[i], DIV);
      uart_bit(1'b1, DIV);
    end
  endtask

  // send with a stretched/shrunk bit period (per-mille of nominal)
  task uart_send_drift(input [7:0] v, input integer permille);
    integer i, c;
    begin
      c = (DIV * permille) / 1000;
      uart_bit(1'b0, c);
      for (i = 0; i < 8; i = i + 1) uart_bit(v[i], c);
      uart_bit(1'b1, DIV);
    end
  endtask

  // ---------------------------------------------------------- UART capturing
  // status: 0 = got a byte, 1 = timeout (line silent), 2 = desync (bad
  // stop bit - normal when listening starts mid-byte; caller resyncs,
  // the same discipline the cocotb capture uses)
  task uart_rx_byte(input integer timeout_cycles,
                    output integer status, output [7:0] b);
    integer n, i;
    begin
      // sample AFTER nonblocking updates settle (#1 past the edge) -
      // the same end-of-timestep discipline cocotb's ReadOnly gives;
      // sampling raw at the edge reads the PREVIOUS bit whenever a
      // transition lands on the sample edge
      status = 1; b = 8'h00; n = 0;
      while (n < timeout_cycles && uart_tx !== 1'b0) begin
        @(posedge clk); #1; n = n + 1;
      end
      if (uart_tx === 1'b0) begin
        repeat (DIV / 2) @(posedge clk);
        for (i = 0; i < 8; i = i + 1) begin
          repeat (DIV) @(posedge clk);
          #1; b[i] = uart_tx;
        end
        repeat (DIV) @(posedge clk);   // stop bit position
        #1; status = (uart_tx === 1'b1) ? 0 : 2;
      end
    end
  endtask

  // hunt for a byte value among telemetry traffic; desyncs just resync
  task uart_expect(input [7:0] want, input integer tries,
                   input [8*64-1:0] what);
    integer k, st;
    reg [7:0] b;
    begin
      for (k = 0; k < tries; k = k + 1) begin
        uart_rx_byte(TLM_CYCLES, st, b);
        check(st != 1, {what, " (line went silent)"});
        if (st == 0 && b === want) k = tries + 7;   // found
      end
      check(k > tries, what);
    end
  endtask

  reg [7:0] frame [0:FRAME_LEN-1];

  task capture_frame(input [8*64-1:0] what);
    integer got, i, st;
    reg [7:0] b;
    begin
      got = 0;
      while (got == 0) begin
        uart_rx_byte(TLM_CYCLES, st, b);
        check(st != 1, {what, " (line went silent hunting sync)"});
        if (st == 0 && b === 8'h5A) begin
          uart_rx_byte(30 * DIV, st, b);
          if (st == 0 && b === 8'h33) begin
            frame[0] = 8'h5A; frame[1] = 8'h33;
            for (i = 2; i < FRAME_LEN; i = i + 1) begin
              uart_rx_byte(30 * DIV, st, b);
              check(st == 0, {what, " (frame truncated)"});
              frame[i] = b;
            end
            got = 1;
          end
        end
      end
    end
  endtask

  function [7:0] frame_xor;
    input dummy;
    integer i;
    begin
      frame_xor = 8'h00;
      for (i = 0; i < FRAME_LEN - 1; i = i + 1)
        frame_xor = frame_xor ^ frame[i];
    end
  endfunction

  function [15:0] ctr16;
    input integer idx;   // byte index of the high byte
    ctr16 = {frame[idx], frame[idx + 1]};
  endfunction

  // ------------------------------------------------------------------- reset
  task chip_boot;
    begin
      ena = 1'b1; ui_in = 8'h08; uio_in = 8'h00; loop_en = 1'b0;
      rst_n = 1'b0;
      repeat (8) @(posedge clk);
      rst_n = 1'b1;
      // twice the nominal boot, matching the cocotb integration suite:
      // the bit-serial CPU needs the second window to finish crt0 and
      // reach the command loop before a scenario talks to it
      repeat (2 * BOOT_CYCLES) @(posedge clk);
    end
  endtask

  // --------------------------------------------------------- fault injection
  // one "particle" into replica A of a named counter island: flip a low
  // bit through exactly one clock edge, then release. Targets are the
  // REPLICAS - the voter output is never touched (the cocotb lesson).
  task flip_hk_island(input integer which);
    begin
      @(posedge clk);
      case (which)
        0: force dut.u_hk.u_c_plain.u_ff_a.q_o =
             dut.u_hk.u_c_plain.u_ff_a.q_o ^ 16'h0001;
        1: force dut.u_hk.u_c_raw_a.u_ff_a.q_o =
             dut.u_hk.u_c_raw_a.u_ff_a.q_o ^ 16'h0002;
        2: force dut.u_hk.u_warm.u_ff_a.q_o =
             dut.u_hk.u_warm.u_ff_a.q_o ^ 6'h04;
        3: force dut.u_hk.u_mode.u_ff_a.q_o =
             dut.u_hk.u_mode.u_ff_a.q_o ^ 2'h1;
        default: force dut.u_hk.u_c_esc_b.u_ff_a.q_o =
             dut.u_hk.u_c_esc_b.u_ff_a.q_o ^ 16'h0008;
      endcase
      @(posedge clk);
      #1;
      case (which)
        0: release dut.u_hk.u_c_plain.u_ff_a.q_o;
        1: release dut.u_hk.u_c_raw_a.u_ff_a.q_o;
        2: release dut.u_hk.u_warm.u_ff_a.q_o;
        3: release dut.u_hk.u_mode.u_ff_a.q_o;
        default: release dut.u_hk.u_c_esc_b.u_ff_a.q_o;
      endcase
    end
  endtask

  // the registered escape geometry: same bit, TWO replicas, one cycle
  task double_hit_plain;
    begin
      @(posedge clk);
      force dut.u_hk.u_c_plain.u_ff_a.q_o =
        dut.u_hk.u_c_plain.u_ff_a.q_o ^ 16'h0010;
      force dut.u_hk.u_c_plain.u_ff_b.q_o =
        dut.u_hk.u_c_plain.u_ff_b.q_o ^ 16'h0010;
      @(posedge clk);
      #1;
      release dut.u_hk.u_c_plain.u_ff_a.q_o;
      release dut.u_hk.u_c_plain.u_ff_b.q_o;
    end
  endtask

  // ---------------------------------------------------------------- scenarios
  task scn_boot_frame;
    begin
      cur_scn = "boot_frame"; chip_boot;
      capture_frame("no frame after boot");
      check(frame_xor(1'b0) === frame[FRAME_LEN-1], "frame checksum");
      check(ctr16(5) === 16'h0 && ctr16(7) === 16'h0 &&
            ctr16(9) === 16'h0 && ctr16(11) === 16'h0,
            "beam counters not zero at boot");
    end
  endtask

  task scn_cpu_alive;
    reg [7:0] sig1, sig2;
    begin
      cur_scn = "cpu_alive"; chip_boot;
      capture_frame("no first frame");
      sig1 = frame[16];
      capture_frame("no second frame");
      sig2 = frame[16];
      check(sig1 !== 8'h00 || sig2 !== 8'h00, "CPU signature stuck at zero");
      check(sig1 !== sig2, "CPU signature frozen between frames");
    end
  endtask

  task scn_echo_basic;
    begin
      cur_scn = "echo_basic"; chip_boot;
      uart_send(8'h41);
      uart_expect(8'h42, 40, "echo 0x41->0x42 never appeared");
    end
  endtask

  task scn_echo_sweep;
    begin
      cur_scn = "echo_sweep"; chip_boot;
      // edge values, including bytes that collide with the frame sync
      uart_send(8'h00); uart_expect(8'h01, 40, "echo of 0x00");
      uart_send(8'hFE); uart_expect(8'hFF, 40, "echo of 0xFE");
      uart_send(8'h5A); uart_expect(8'h5B, 40, "echo of sync byte 0x5A");
      uart_send(8'h33); uart_expect(8'h34, 40, "echo of sync byte 0x33");
    end
  endtask

  task scn_cmd_fuzz;
    integer i;
    begin
      cur_scn = "cmd_fuzz"; chip_boot;
      // a spread of junk commands the firmware does not define
      uart_send(8'h07); uart_send(8'h7F); uart_send(8'h80);
      uart_send(8'hAA); uart_send(8'hF0); uart_send(8'h1B);
      repeat (30_000) @(posedge clk);
      // the computer must still answer
      uart_send(8'h41);
      uart_expect(8'h42, 40, "CPU dead after junk commands");
      // and frames must still carry a valid checksum
      capture_frame("no frame after fuzz");
      check(frame_xor(1'b0) === frame[FRAME_LEN-1], "checksum after fuzz");
    end
  endtask

  task scn_inject_counters;
    begin
      cur_scn = "inject_counters"; chip_boot;
      uart_send("1");            // one A-replica -> RAW_A only
      uart_send("4");            // all-B -> ESC_B only
      capture_frame("no frame after injections");
      if (ctr16(5) === 16'h0) capture_frame("counters never latched");
      check(ctr16(5)  === 16'h1, "RAW_A must read 1");
      check(ctr16(7)  === 16'h0, "ESC_A must stay 0");
      check(ctr16(9)  === 16'h0, "RAW_B must stay 0");
      check(ctr16(11) === 16'h1, "ESC_B must read 1");
      uart_send("C");
      capture_frame("no frame after clear");
      if (ctr16(5) !== 16'h0) capture_frame("clear never latched");
      check(ctr16(5) === 16'h0 && ctr16(11) === 16'h0, "clear failed");
    end
  endtask

  task scn_rom_checksum;
    begin
      cur_scn = "rom_checksum"; chip_boot;
      uart_send("R");
      uart_expect(ROM_SUM, 60, "ROM checksum never answered");
    end
  endtask

  task scn_env_chain;
    begin
      cur_scn = "env_chain"; chip_boot;
      uart_send("E"); uart_expect("e", 40, "'E' never acked");
      uart_send("S"); uart_expect(8'h01, 40, "SET count of 1 never read");
      uart_send("B"); uart_expect(8'h00, 40, "burst count of 0 never read");
    end
  endtask

  task scn_ifc_loopback;
    begin
      cur_scn = "ifc_loopback"; chip_boot;
      loop_en = 1'b1;
      repeat (2_000) @(posedge clk);
      uart_send("k"); uart_expect("b", 40, "CAN beacon never acked");
      uart_send("w"); uart_expect("y", 40, "SpaceWire never reached Run");
      loop_en = 1'b0;
    end
  endtask

  task scn_reset_midframe;
    reg ok; reg [7:0] b;
    begin
      cur_scn = "reset_midframe"; chip_boot;
      // wait for a frame to START, then yank reset in its middle
      uart_rx_byte(TLM_CYCLES, ok, b);
      check(ok, "no traffic before mid-frame reset");
      rst_n = 1'b0;
      repeat (8) @(posedge clk);
      rst_n = 1'b1;
      repeat (BOOT_CYCLES) @(posedge clk);
      capture_frame("no frame after mid-frame reset");
      check(frame_xor(1'b0) === frame[FRAME_LEN-1],
            "checksum after mid-frame reset");
    end
  endtask

  task scn_reset_storm;
    integer i;
    begin
      cur_scn = "reset_storm";
      ena = 1'b1; ui_in = 8'h08; uio_in = 8'h00; loop_en = 1'b0;
      for (i = 0; i < 5; i = i + 1) begin
        rst_n = 1'b0; repeat (3 + i) @(posedge clk);
        rst_n = 1'b1; repeat (50 + 17 * i) @(posedge clk);
      end
      rst_n = 1'b0; repeat (8) @(posedge clk); rst_n = 1'b1;
      repeat (BOOT_CYCLES) @(posedge clk);
      capture_frame("no frame after reset storm");
      check(frame_xor(1'b0) === frame[FRAME_LEN-1],
            "checksum after reset storm");
      uart_send(8'h41);
      uart_expect(8'h42, 40, "CPU dead after reset storm");
    end
  endtask

  task scn_uart_glitch;
    begin
      cur_scn = "uart_glitch"; chip_boot;
      // a runt low far shorter than a start bit
      uart_bit(1'b0, 3);
      uart_bit(1'b1, 3 * DIV);
      // and a half-bit runt, the nastier case
      uart_bit(1'b0, DIV / 2 - 2);
      uart_bit(1'b1, 3 * DIV);
      // the line must still decode a real byte
      uart_send(8'h41);
      uart_expect(8'h42, 40, "RX wedged by runt start bits");
    end
  endtask

  task scn_baud_drift;
    begin
      cur_scn = "baud_drift"; chip_boot;
      uart_send_drift(8'h41, 950);    // -5%
      uart_expect(8'h42, 40, "echo at -5% baud");
      uart_send_drift(8'h41, 1050);   // +5%
      uart_expect(8'h42, 40, "echo at +5% baud");
    end
  endtask

  task scn_uart_flood;
    integer i;
    begin
      cur_scn = "uart_flood"; chip_boot;
      // 32 back-to-back bytes at line rate, no gaps
      for (i = 0; i < 32; i = i + 1) uart_send(8'h55);
      repeat (40_000) @(posedge clk);
      uart_send(8'h41);
      uart_expect(8'h42, 40, "CPU dead after UART flood");
      capture_frame("no frame after flood");
      check(frame_xor(1'b0) === frame[FRAME_LEN-1], "checksum after flood");
    end
  endtask

  task scn_tmr_flip_storm;
    integer i;
    begin
      cur_scn = "tmr_flip_storm"; chip_boot;
      // upsets raining on live counters while commands fly
      for (i = 0; i < 25; i = i + 1) begin
        flip_hk_island(i % 5);
        repeat (200 + 37 * i) @(posedge clk);
      end
      // voted state never wavered: the beam counters still read zero
      uart_send("C");
      capture_frame("no frame during flip storm");
      capture_frame("no second frame during flip storm");
      check(frame_xor(1'b0) === frame[FRAME_LEN-1], "checksum in storm");
      check(ctr16(5) === 16'h0 && ctr16(7) === 16'h0 &&
            ctr16(9) === 16'h0 && ctr16(11) === 16'h0,
            "healed flips must not tick beam counters");
      uart_send(8'h41);
      uart_expect(8'h42, 40, "CPU lost in the flip storm");
    end
  endtask

  task scn_double_hit;
    begin
      cur_scn = "double_hit"; chip_boot;
      // the registered failure geometry corrupts state - the claim is
      // never "no corruption", it is "the chip survives and keeps
      // telling the truth"
      double_hit_plain;
      capture_frame("no frame after double hit");
      check(frame_xor(1'b0) === frame[FRAME_LEN-1],
            "checksum after double hit");
      uart_send(8'h41);
      uart_expect(8'h42, 40, "CPU dead after double hit");
    end
  endtask

  task scn_soak;
    integer i;
    begin
      cur_scn = "soak"; chip_boot;
      for (i = 0; i < 6; i = i + 1) begin
        capture_frame("soak frame missing");
        check(frame_xor(1'b0) === frame[FRAME_LEN-1], "soak checksum");
        check(ctr16(5) === 16'h0 && ctr16(7) === 16'h0 &&
              ctr16(9) === 16'h0 && ctr16(11) === 16'h0,
              "false positive: beam counter ticked with no injection");
      end
    end
  endtask

  // ------------------------------------------------------------------ runner
  reg [8*24-1:0] want_scn;
  reg run_all;

  task run_one(input [8*24-1:0] name);
    begin
      if (run_all || want_scn == name) begin
        scenarios_run = scenarios_run + 1;
        case (name)
          "boot_frame":      scn_boot_frame;
          "cpu_alive":       scn_cpu_alive;
          "echo_basic":      scn_echo_basic;
          "echo_sweep":      scn_echo_sweep;
          "cmd_fuzz":        scn_cmd_fuzz;
          "inject_counters": scn_inject_counters;
          "rom_checksum":    scn_rom_checksum;
          "env_chain":       scn_env_chain;
          "ifc_loopback":    scn_ifc_loopback;
          "reset_midframe":  scn_reset_midframe;
          "reset_storm":     scn_reset_storm;
          "uart_glitch":     scn_uart_glitch;
          "baud_drift":      scn_baud_drift;
          "uart_flood":      scn_uart_flood;
          "tmr_flip_storm":  scn_tmr_flip_storm;
          "double_hit":      scn_double_hit;
          "soak":            scn_soak;
        endcase
        $display("PASS [%0s] (%0d checks so far)", name, checks_done);
      end
    end
  endtask

  initial begin
    clk = 1'b0; checks_done = 0; scenarios_run = 0;
    run_all = !$value$plusargs("SCENARIO=%s", want_scn);

    run_one("boot_frame");
    run_one("cpu_alive");
    run_one("echo_basic");
    run_one("echo_sweep");
    run_one("cmd_fuzz");
    run_one("inject_counters");
    run_one("rom_checksum");
    run_one("env_chain");
    run_one("ifc_loopback");
    run_one("reset_midframe");
    run_one("reset_storm");
    run_one("uart_glitch");
    run_one("baud_drift");
    run_one("uart_flood");
    run_one("tmr_flip_storm");
    run_one("double_hit");
    run_one("soak");

    if (scenarios_run == 0) begin
      $display("FAIL: unknown scenario +SCENARIO=%0s", want_scn);
      $fatal(1);
    end
    $display("SV_SCENARIOS: PASS scenarios=%0d checks=%0d",
             scenarios_run, checks_done);
    $finish;
  end

  // global watchdog: nothing in this bench may hang silently
  initial begin
    #(64'd1_000_000_000 * 40);   // 40 ms of sim time, far past any scenario
    $display("FAIL [%0s] bench watchdog: scenario hung", cur_scn);
    $fatal(1);
  end

endmodule

`default_nettype wire
