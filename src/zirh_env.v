// =============================================================================
// ZIRH-2 - environment monitor: TID sensor + SET catcher + burst correlator
// zirh_env.v
//
// Three pin-free instruments that widen the chip from an SEU counter into
// a combined radiation-effects observatory, all read over the existing
// UART command path (hk registers 0x38/0x3C):
//
//   RING-OSCILLATOR TID SENSOR - a 64-stage enable-gated ring oscillator
//   counted over a fixed 1024-cycle window. Total ionizing dose shifts
//   transistor thresholds and the oscillation frequency drifts with
//   accumulated dose (demonstrated from 28 nm FD-SOI to 250 nm bulk in
//   the literature); repeated 'T' readings over a mission plot the dose
//   curve with zero analog circuitry. The ripple counter lives in the
//   oscillator clock domain and is read only when the window controller
//   is idle, so no synchronizer crosses a running clock.
//
//   SET CATCHER - a quiet 64-stage minimum-drive inverter chain watched
//   by a cross-coupled NAND catch latch. A particle strike anywhere in
//   the chain appears at the output as a positive glitch (idle level 0)
//   and sets the latch regardless of how short the pulse is - the classic
//   self-triggered capture structure (Narasimham et al.; also built on
//   IHP 250 nm bulk). The latch is synchronized, counted (TMR) and
//   automatically re-armed. Combinational transients are a different
//   physical observable than the flop upsets the rings measure - this is
//   the chip's third particle detector, and the firmware can fire a test
//   pulse through the same chain to prove the detector alive in flight.
//
//   BURST CORRELATOR - counts ring-event onsets that arrive within 16
//   cycles of a previous onset. Spatially or temporally clustered strikes
//   (MBU-like bursts, shallow-angle tracks) show up as a climbing burst
//   count against the Poisson-flat background; a cheap statistic the
//   ground cannot recover from saturating counters after the fact.
//
// The oscillator and the catch chain are hand-instantiated SG13G2 cells
// inside keep_hierarchy islands with (* keep *) on every instance -
// synthesis would otherwise collapse an inverter chain to a wire. RTL
// simulation swaps them for behavioral models under ZIRH_SIM_ENV (a
// zero-delay combinational loop would hang event-driven simulation);
// gate-level simulation must simply never enable the oscillator, which
// is why the 'T' exercise is RTL-only.
// =============================================================================

`default_nettype none

// --- ring oscillator + ripple counter (own clock domain) ---------------------
(* keep_hierarchy *) module zirh_env_ro (
    input  wire        clk,      // used by the simulation model only
    input  wire        en_i,     // run the loop
    input  wire        clr_i,    // async counter clear (assert only when idle)
    output wire [15:0] cnt_o
);
`ifdef ZIRH_SIM_ENV
    // behavioral stand-in: one count per clk cycle while enabled, so a
    // 1024-cycle window reads back ~1024 - the control path is what the
    // simulation verifies, the real frequency only exists in silicon
    wire ro_out = en_i & clk;
`else
    localparam integer STAGES = 64;   // even; NAND adds the odd inversion
    wire [STAGES:0] n;
    (* keep *) sg13g2_nand2_1 u_gate (.A(en_i), .B(n[STAGES]), .Y(n[0]));
    genvar i;
    generate
        for (i = 0; i < STAGES; i = i + 1) begin : g_inv
            (* keep *) sg13g2_inv_1 u_inv (.A(n[i]), .Y(n[i+1]));
        end
    endgenerate
    wire ro_out = n[STAGES];
    wire _unused_clk = clk;
`endif

    // asynchronous ripple counter: stage j+1 clocks on stage j's falling
    // edge, so only the first flop sees the full oscillator rate
    wire [16:0] rc;
    assign rc[0] = ro_out;
    genvar j;
    generate
        for (j = 0; j < 16; j = j + 1) begin : g_rc
            reg q;
            always @(posedge rc[j] or posedge clr_i)
                if (clr_i) q <= 1'b0;
                else       q <= ~q;
            assign rc[j+1]  = ~q;
            assign cnt_o[j] = q;
        end
    endgenerate

endmodule

// --- quiet chain + catch latch (fully combinational) -------------------------
(* keep_hierarchy *) module zirh_env_set (
    input  wire test_i,     // chain input, idle 0; pulse for self-test
    input  wire arm_n_i,    // active low: clear and re-arm the latch
    output wire caught_o
);
`ifdef ZIRH_SIM_ENV
    wire chain_out = test_i;
    reg q;
    always @* begin
        if (!arm_n_i)       q = 1'b0;
        else if (chain_out) q = 1'b1;
    end
    assign caught_o = q;
`else
    localparam integer STAGES = 64;   // even: output follows the input
    wire [STAGES:0] c;
    assign c[0] = test_i;
    genvar i;
    generate
        for (i = 0; i < STAGES; i = i + 1) begin : g_inv
            (* keep *) sg13g2_inv_1 u_inv (.A(c[i]), .Y(c[i+1]));
        end
    endgenerate
    wire chain_out = c[STAGES];

    // any strike in the chain reaches the idle-low output as a positive
    // glitch; ~chain_out is the active-low set of a cross-coupled NAND
    // latch, which holds the event until the controller re-arms it
    wire s_n, q, qb;
    (* keep *) sg13g2_nand2_1 u_sn (.A(chain_out), .B(chain_out), .Y(s_n));
    (* keep *) sg13g2_nand2_1 u_l1 (.A(s_n),      .B(qb),        .Y(q));
    (* keep *) sg13g2_nand2_1 u_l2 (.A(arm_n_i),  .B(q),         .Y(qb));
    assign caught_o = q;
`endif
endmodule

// --- controller (clk domain, counters TMR per chip philosophy) ---------------
module zirh_env #(
    parameter integer WIN_LOG2 = 10,   // oscillator window, cycles
    parameter integer SETTLE   = 8     // ripple settle tail before busy drops
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start_i,     // one-cycle pulse: run an RO window
    input  wire        test_i,      // one-cycle pulse: SET chain self-test
    input  wire        clear_i,     // clear set/burst counters
    input  wire        evt_i,       // any ring event (level, edge-filtered here)

    output wire [31:0] ro_word_o,   // {busy, 15'h0, count}
    output wire [31:0] sb_word_o,   // {16'h0, burst, set_count}
    output wire        err_o        // own TMR mismatch, pulse
);

    localparam integer WW = WIN_LOG2 + 1;
    localparam [WW-1:0] WIN_LOAD = (1 << WIN_LOG2) + SETTLE;

    // --- oscillator window ---------------------------------------------------
    wire [WW-1:0] win_q;
    wire          win_err;
    wire          busy    = |win_q;
    wire          ro_en   = (win_q > SETTLE[WW-1:0]);
    wire          start_f = start_i & ~busy;

    zirh_tmr_reg #(.WIDTH(WW)) u_win (
        .clk(clk), .rst_n(rst_n),
        .en_i(start_f | busy),
        .d_i(start_f ? WIN_LOAD : win_q - {{(WW-1){1'b0}}, 1'b1}),
        .q_o(win_q), .err_o(win_err));

    wire [15:0] ro_cnt;
    zirh_env_ro u_ro (
        .clk(clk), .en_i(ro_en), .clr_i(start_f | ~rst_n), .cnt_o(ro_cnt));

    // --- SET catch, synchronize, count, re-arm -------------------------------
    // rearm loads at reset so the latch is held cleared through the X window
    reg [2:0] rearm;
    reg [1:0] tpulse;
    wire      caught;

    zirh_env_set u_set (
        .test_i(|tpulse), .arm_n_i(~(|rearm)), .caught_o(caught));

    reg [1:0] csync;
    reg       cprev;
    wire      set_rise = csync[1] & ~cprev;

    always @(posedge clk) begin
        if (!rst_n) begin
            rearm  <= 3'd6;
            tpulse <= 2'd0;
            csync  <= 2'd0;
            cprev  <= 1'b0;
        end else begin
            csync <= {csync[0], caught};
            cprev <= csync[1];
            if (test_i)          tpulse <= 2'd3;
            else if (|tpulse)    tpulse <= tpulse - 2'd1;
            if (set_rise)        rearm  <= 3'd6;
            else if (|rearm)     rearm  <= rearm - 3'd1;
        end
    end

    wire [7:0] set_q;
    wire       set_err;
    zirh_tmr_reg #(.WIDTH(8)) u_setc (
        .clk(clk), .rst_n(rst_n),
        .en_i(clear_i | (set_rise & (set_q != 8'hFF))),
        .d_i(clear_i ? 8'h0 : set_q + 8'h1),
        .q_o(set_q), .err_o(set_err));

    // --- burst correlator ----------------------------------------------------
    reg evt_r;
    always @(posedge clk) begin
        if (!rst_n) evt_r <= 1'b0;
        else        evt_r <= evt_i;
    end
    wire evt_rise = evt_i & ~evt_r;

    wire [4:0] btim_q;
    wire       btim_err;
    zirh_tmr_reg #(.WIDTH(5)) u_btim (
        .clk(clk), .rst_n(rst_n),
        .en_i(evt_rise | (|btim_q)),
        .d_i(evt_rise ? 5'd16 : btim_q - 5'd1),
        .q_o(btim_q), .err_o(btim_err));

    wire [7:0] burst_q;
    wire       burst_err;
    zirh_tmr_reg #(.WIDTH(8)) u_burst (
        .clk(clk), .rst_n(rst_n),
        .en_i(clear_i | (evt_rise & (|btim_q) & (burst_q != 8'hFF))),
        .d_i(clear_i ? 8'h0 : burst_q + 8'h1),
        .q_o(burst_q), .err_o(burst_err));

    // --- exports -------------------------------------------------------------
    assign ro_word_o = {busy, 15'h0, ro_cnt};
    assign sb_word_o = {16'h0, burst_q, set_q};
    assign err_o     = win_err | set_err | btim_err | burst_err;

endmodule

`default_nettype wire
