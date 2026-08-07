// =============================================================================
// ZIRH-2 - housekeeping block: SEU monitor v2 + ECC counters + CPU signature
// zirh_hk.v
//
// The measurement heart of ZIRH-2, as one bus slave. Three circulating
// rings of equal length N=64, all fed by the shared pattern source:
//
//   PLAIN    : 128 ordinary flops - cross-section reference, continuity
//              with ZIRH-1's data
//   TMR A    : 3 replicas as zirh_tmr_ff64 instances - the CONSTRAINED
//              chain: at hardening time the three modules bind to
//              pre-hardened macros pinned to separated coordinates
//   TMR B    : 3 replicas as plain zirh_tmr_ff #(64) - the TOOL-PLACED
//              chain, identical logic, no placement constraint
//
// ESCAPE(A) versus ESCAPE(B) under the same beam is the ZIRH-2 headline
// number: what does placement separation buy, measured on one die.
//
// Also counted here, because telemetry needs them in one snapshot: the ECC
// RAM's corrected/uncorrected events (8-bit saturating, TMR'd) and the
// CPU's rolling liveness signature (written by firmware over the bus; a
// stuck CPU stops updating it and cpu_alive_o stops pulsing).
//
// Register map (word offsets in slot 3, base 0x3000):
//   0x00 SIG     RO  {8'h5A, 8'h32, 8'h00, 4'b0, armed, infra_seen, mode}
//   0x04 CTRL    RW  [1:0] mode; write bit 8 = clear all counters
//   0x08 CPU_SIG RW  [7:0] firmware heartbeat signature
//   0x0C INJECT  WO  0 plain, 1 one A-replica, 2 all-A (escape),
//                    3 one B-replica, 4 all-B
//   0x10 PLAIN   RO  0x14 RAW_A  0x18 ESC_A  0x1C RAW_B  0x20 ESC_B
//   0x24 ECC_C   RO  0x28 ECC_U
// =============================================================================

`default_nettype none

module zirh_hk #(
    parameter integer N  = 64,    // ring length, must be even
    parameter integer CW = 16
) (
    input  wire        clk,
    input  wire        rst_n,

    // bus slave (slot 3)
    input  wire        cyc_i,
    input  wire [31:0] adr_i,
    input  wire [31:0] dat_i,
    input  wire        we_i,
    output wire [31:0] rdt_o,
    output wire        ack_o,

    // ECC RAM event pulses (from zirh_soc)
    input  wire        ecc_corr_i,
    input  wire        ecc_uncorr_i,

    // snapshot exports for zirh_tlm2
    output wire [CW-1:0] cnt_plain_o,
    output wire [CW-1:0] cnt_raw_a_o,
    output wire [CW-1:0] cnt_esc_a_o,
    output wire [CW-1:0] cnt_raw_b_o,
    output wire [CW-1:0] cnt_esc_b_o,
    output wire [7:0]    cnt_ecc_c_o,
    output wire [7:0]    cnt_ecc_u_o,
    output wire [7:0]    cpu_sig_o,
    output wire [1:0]    mode_o,
    output wire          armed_o,
    output wire          err_infra_o,   // own TMR mismatches, pulse

    // live pulses for pins
    output wire        evt_o,           // any ring event
    output wire        cpu_alive_o      // pulse per CPU_SIG write
);

    localparam integer INJ_POS = N / 2;
    localparam integer WW = $clog2(N + 5);
    localparam [WW-1:0] WARM_LOAD = N + 4;

    // --- bus decode ---------------------------------------------------------
    wire [3:0] reg_sel = adr_i[5:2];
    wire wr      = cyc_i & we_i;
    wire wr_ctrl = wr & (reg_sel == 4'h1);
    wire wr_sig  = wr & (reg_sel == 4'h2);
    wire wr_inj  = wr & (reg_sel == 4'h3);
    wire clear   = wr_ctrl & dat_i[8];

    // one-shot injection strobes (bus writes last 2 cycles; fire once)
    reg inj_seen;
    always @(posedge clk) begin
        if (!rst_n) inj_seen <= 1'b0;
        else        inj_seen <= wr_inj;
    end
    wire inj_fire = wr_inj & ~inj_seen;

    wire inj_plain = inj_fire & (dat_i[2:0] == 3'd0);
    wire inj_a_one = inj_fire & (dat_i[2:0] == 3'd1);
    wire inj_a_all = inj_fire & (dat_i[2:0] == 3'd2);
    wire inj_b_one = inj_fire & (dat_i[2:0] == 3'd3);
    wire inj_b_all = inj_fire & (dat_i[2:0] == 3'd4);

    // --- pattern source + warm-up (as v1) -----------------------------------
    wire [1:0] mode_q;
    wire       mode_err, phase_err, warm_err;
    wire       phase_q;

    zirh_tmr_reg #(.WIDTH(2)) u_mode (
        .clk(clk), .rst_n(rst_n), .en_i(wr_ctrl), .d_i(dat_i[1:0]),
        .q_o(mode_q), .err_o(mode_err));

    zirh_tmr_reg #(.WIDTH(1)) u_phase (
        .clk(clk), .rst_n(rst_n), .en_i(1'b1), .d_i(~phase_q),
        .q_o(phase_q), .err_o(phase_err));

    wire in_bit       = mode_q[1] ? phase_q : mode_q[0];
    wire expected_bit = in_bit;          // N even

    wire [WW-1:0] warm_q;
    wire mode_change = wr_ctrl & (dat_i[1:0] != mode_q);

    zirh_tmr_reg #(.WIDTH(WW), .RESET_VALUE(WARM_LOAD)) u_warm (
        .clk(clk), .rst_n(rst_n),
        .en_i(mode_change | (|warm_q)),
        .d_i(mode_change ? WARM_LOAD : warm_q - {{(WW-1){1'b0}}, 1'b1}),
        .q_o(warm_q), .err_o(warm_err));

    wire armed = (warm_q == {WW{1'b0}});
    assign armed_o = armed;
    assign mode_o  = mode_q;

    // --- PLAIN ring ---------------------------------------------------------
    reg  [N-1:0] plain_q;
    wire [N-1:0] plain_nxt = {plain_q[N-2:0], in_bit}
                             ^ ({{(N-1){1'b0}}, inj_plain} << INJ_POS);
    always @(posedge clk) begin
        if (!rst_n) plain_q <= {N{1'b0}};
        else        plain_q <= plain_nxt;
    end
    wire plain_evt = armed & (plain_q[N-1] != expected_bit);

    // --- TMR ring A: the constrained chain (macro-bound at hardening) -------
    wire [N-1:0] a_qa, a_qb, a_qc;
    wire [N-1:0] a_voted = (a_qa & a_qb) | (a_qb & a_qc) | (a_qa & a_qc);
    wire [N-1:0] inj_mask = {{(N-1){1'b0}}, 1'b1} << INJ_POS;
    wire [N-1:0] a_base = {a_voted[N-2:0], in_bit}
                          ^ (inj_a_all ? inj_mask : {N{1'b0}});
    wire [N-1:0] a_d_a  = a_base ^ (inj_a_one ? inj_mask : {N{1'b0}});

    // At the real N the concrete wrapper is used so the three instances can
    // bind to placement-constrained macros at hardening time; the sim-only
    // small-N override falls back to the functionally identical library FF.
    generate
        if (N == 64) begin : g_a_macro
            zirh_tmr_ff64 u_ff_a (.clk(clk), .rst_n(rst_n), .d_i(a_d_a),  .q_o(a_qa));
            zirh_tmr_ff64 u_ff_b (.clk(clk), .rst_n(rst_n), .d_i(a_base), .q_o(a_qb));
            zirh_tmr_ff64 u_ff_c (.clk(clk), .rst_n(rst_n), .d_i(a_base), .q_o(a_qc));
        end else begin : g_a_sim
            zirh_tmr_ff #(.WIDTH(N)) u_ff_a (.clk(clk), .rst_n(rst_n), .d_i(a_d_a),  .q_o(a_qa));
            zirh_tmr_ff #(.WIDTH(N)) u_ff_b (.clk(clk), .rst_n(rst_n), .d_i(a_base), .q_o(a_qb));
            zirh_tmr_ff #(.WIDTH(N)) u_ff_c (.clk(clk), .rst_n(rst_n), .d_i(a_base), .q_o(a_qc));
        end
    endgenerate

    wire raw_a_evt = armed & (|((a_qa ^ a_qb) | (a_qb ^ a_qc) | (a_qa ^ a_qc)));
    wire esc_a_evt = armed & (a_voted[N-1] != expected_bit);

    // --- TMR ring B: identical logic, tool-placed ---------------------------
    wire [N-1:0] b_qa, b_qb, b_qc;
    wire [N-1:0] b_voted = (b_qa & b_qb) | (b_qb & b_qc) | (b_qa & b_qc);
    wire [N-1:0] b_base = {b_voted[N-2:0], in_bit}
                          ^ (inj_b_all ? inj_mask : {N{1'b0}});
    wire [N-1:0] b_d_a  = b_base ^ (inj_b_one ? inj_mask : {N{1'b0}});

    zirh_tmr_ff #(.WIDTH(N)) u_ch_b_a (.clk(clk), .rst_n(rst_n), .d_i(b_d_a),  .q_o(b_qa));
    zirh_tmr_ff #(.WIDTH(N)) u_ch_b_b (.clk(clk), .rst_n(rst_n), .d_i(b_base), .q_o(b_qb));
    zirh_tmr_ff #(.WIDTH(N)) u_ch_b_c (.clk(clk), .rst_n(rst_n), .d_i(b_base), .q_o(b_qc));

    wire raw_b_evt = armed & (|((b_qa ^ b_qb) | (b_qb ^ b_qc) | (b_qa ^ b_qc)));
    wire esc_b_evt = armed & (b_voted[N-1] != expected_bit);

    // --- counters -----------------------------------------------------------
    localparam [CW-1:0] CMAX  = {CW{1'b1}};
    localparam [7:0]    CMAX8 = 8'hFF;

    wire [CW-1:0] c_plain, c_raw_a, c_esc_a, c_raw_b, c_esc_b;
    wire [7:0]    c_ecc_c, c_ecc_u;
    wire e_p, e_ra, e_ea, e_rb, e_eb, e_ec, e_eu;

    zirh_tmr_reg #(.WIDTH(CW)) u_c_plain (
        .clk(clk), .rst_n(rst_n),
        .en_i(clear | (plain_evt & (c_plain != CMAX))),
        .d_i(clear ? {CW{1'b0}} : c_plain + {{(CW-1){1'b0}}, 1'b1}),
        .q_o(c_plain), .err_o(e_p));
    zirh_tmr_reg #(.WIDTH(CW)) u_c_raw_a (
        .clk(clk), .rst_n(rst_n),
        .en_i(clear | (raw_a_evt & (c_raw_a != CMAX))),
        .d_i(clear ? {CW{1'b0}} : c_raw_a + {{(CW-1){1'b0}}, 1'b1}),
        .q_o(c_raw_a), .err_o(e_ra));
    zirh_tmr_reg #(.WIDTH(CW)) u_c_esc_a (
        .clk(clk), .rst_n(rst_n),
        .en_i(clear | (esc_a_evt & (c_esc_a != CMAX))),
        .d_i(clear ? {CW{1'b0}} : c_esc_a + {{(CW-1){1'b0}}, 1'b1}),
        .q_o(c_esc_a), .err_o(e_ea));
    zirh_tmr_reg #(.WIDTH(CW)) u_c_raw_b (
        .clk(clk), .rst_n(rst_n),
        .en_i(clear | (raw_b_evt & (c_raw_b != CMAX))),
        .d_i(clear ? {CW{1'b0}} : c_raw_b + {{(CW-1){1'b0}}, 1'b1}),
        .q_o(c_raw_b), .err_o(e_rb));
    zirh_tmr_reg #(.WIDTH(CW)) u_c_esc_b (
        .clk(clk), .rst_n(rst_n),
        .en_i(clear | (esc_b_evt & (c_esc_b != CMAX))),
        .d_i(clear ? {CW{1'b0}} : c_esc_b + {{(CW-1){1'b0}}, 1'b1}),
        .q_o(c_esc_b), .err_o(e_eb));
    zirh_tmr_reg #(.WIDTH(8)) u_c_ecc_c (
        .clk(clk), .rst_n(rst_n),
        .en_i(clear | (ecc_corr_i & (c_ecc_c != CMAX8))),
        .d_i(clear ? 8'h0 : c_ecc_c + 8'h1),
        .q_o(c_ecc_c), .err_o(e_ec));
    zirh_tmr_reg #(.WIDTH(8)) u_c_ecc_u (
        .clk(clk), .rst_n(rst_n),
        .en_i(clear | (ecc_uncorr_i & (c_ecc_u != CMAX8))),
        .d_i(clear ? 8'h0 : c_ecc_u + 8'h1),
        .q_o(c_ecc_u), .err_o(e_eu));

    // --- CPU signature (plain: firmware rewrites it constantly) -------------
    reg [7:0] cpu_sig;
    reg       cpu_alive_r;
    reg       sig_seen;
    always @(posedge clk) begin
        if (!rst_n) begin
            cpu_sig     <= 8'h00;
            cpu_alive_r <= 1'b0;
            sig_seen    <= 1'b0;
        end else begin
            if (wr_sig) cpu_sig <= dat_i[7:0];
            sig_seen    <= wr_sig;
            cpu_alive_r <= wr_sig & ~sig_seen;   // one pulse per bus write
        end
    end

    // --- infra sticky (for SIG readback) + exports --------------------------
    wire infra = mode_err | phase_err | warm_err |
                 e_p | e_ra | e_ea | e_rb | e_eb | e_ec | e_eu;

    reg infra_seen;
    always @(posedge clk) begin
        if (!rst_n)       infra_seen <= 1'b0;
        else if (clear)   infra_seen <= 1'b0;
        else if (infra)   infra_seen <= 1'b1;
    end

    assign cnt_plain_o = c_plain;
    assign cnt_raw_a_o = c_raw_a;
    assign cnt_esc_a_o = c_esc_a;
    assign cnt_raw_b_o = c_raw_b;
    assign cnt_esc_b_o = c_esc_b;
    assign cnt_ecc_c_o = c_ecc_c;
    assign cnt_ecc_u_o = c_ecc_u;
    assign cpu_sig_o   = cpu_sig;
    assign err_infra_o = infra;
    assign evt_o       = plain_evt | raw_a_evt | esc_a_evt | raw_b_evt | esc_b_evt;
    assign cpu_alive_o = cpu_alive_r;

    // --- readback -----------------------------------------------------------
    assign rdt_o =
        (reg_sel == 4'h0) ? {8'h5A, 8'h32, 8'h00, 4'b0, armed, infra_seen, mode_q} :
        (reg_sel == 4'h1) ? {30'h0, mode_q} :
        (reg_sel == 4'h2) ? {24'h0, cpu_sig} :
        (reg_sel == 4'h4) ? {{(32-CW){1'b0}}, c_plain} :
        (reg_sel == 4'h5) ? {{(32-CW){1'b0}}, c_raw_a} :
        (reg_sel == 4'h6) ? {{(32-CW){1'b0}}, c_esc_a} :
        (reg_sel == 4'h7) ? {{(32-CW){1'b0}}, c_raw_b} :
        (reg_sel == 4'h8) ? {{(32-CW){1'b0}}, c_esc_b} :
        (reg_sel == 4'h9) ? {24'h0, c_ecc_c} :
        (reg_sel == 4'hA) ? {24'h0, c_ecc_u} :
        32'h0;

    assign ack_o = cyc_i;

endmodule

`default_nettype wire
