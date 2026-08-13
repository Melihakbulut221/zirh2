// =============================================================================
// ZIRH-2 product program P1 - sliced SRAM word: 5 x RM_IHPSG13_1P_1024x8
// zirh_sram39.v
//
// The memory workstream's first real block: a 1024-word x 32-bit
// SECDED-protected memory built from five open-PDK SRAM macros, 8
// stored bits each (4 data slices + 1 parity slice holding the 6
// Hamming bits and the overall bit). The codeword is EXACTLY the flop
// RAM's - the same zirh_secded.vh include, guarded by the same formal
// proof - so beam data from the two memories is directly comparable:
// same code, different storage physics.
//
// Why sliced: a physical multi-bit upset is confined to one macro; at
// most one slice of any logical word is touched per event footprint
// that stays inside a macro, and the per-word SECDED absorbs one
// slice-resident bit. The slicing price and its escape behaviour are
// a placement-A/B-style experiment of their own (PROGRAM.md A2), and
// the c2 column mux inside the macro interleaves adjacent columns
// across two words, degrading small intra-row clusters to one bit per
// word before the slicing argument is even needed.
//
// Bus behaviour (the ROM ack lesson, applied from birth):
//   * the macro reads SYNCHRONOUSLY, so the ack is REGISTERED and
//     lands exactly on the cycle the decoded data is valid - a
//     combinational ack here would hand the CPU stale rubbish one
//     cycle early (measured twice on this project, never again)
//   * read:          issue / decode / registered ack with data
//   * full write:    encode combinational, registered ack
//   * partial write: issue read / decode+merge+write / registered ack
//   * scrub-on-read: a correctable read writes the fixed codeword
//     back in the cycle after the ack; a transaction arriving in that
//     cycle is simply held one cycle (the bus waits on ack anyway)
//
// Events mirror zirh_ecc_ram: evt pulses only when a stored word's
// decode is USED (reads, RMW merges) - full writes over garbage are
// not phantom corrections.
//
// The BIST port set is tied off here; production test wiring is the
// DFT workstream (PROGRAM.md F28), not a bring-up concern.
// =============================================================================

`default_nettype none

module zirh_sram39 (
    input  wire        clk,
    input  wire        rst_n,

    // bus slave: words 0..1023 at adr[11:2]
    input  wire        cyc_i,
    input  wire [31:0] adr_i,
    input  wire [31:0] dat_i,
    input  wire [3:0]  sel_i,
    input  wire        we_i,
    output wire [31:0] rdt_o,
    output wire        ack_o,

    output reg         evt_corr_o,
    output reg         evt_uncorr_o

`ifdef FORMAL
    // same contract as zirh_ecc_ram: fault XOR on the read view only
    , input wire [38:0] f_corrupt_i
`endif
);

    `include "zirh_secded.vh"

    // --- transaction FSM ----------------------------------------------------
    localparam S_IDLE = 1'b0, S_RD = 1'b1;

    reg state;
    wire [9:0] widx = adr_i[11:2];

    wire full_wr = &sel_i;

    // ~ack_q frames the transaction: without it, a master holding cyc
    // through its ack cycle would relaunch the same access and the extra
    // ack would land on someone else's transaction at the bus mux
    wire issue_rd  = (state == S_IDLE) & cyc_i & ~ack_q
                   & (~we_i | (we_i & ~full_wr));
    wire decode_cy = (state == S_RD);

    // --- the five slices ----------------------------------------------------
    // read data returns one cycle after ren; write is same-cycle
    wire [38:0] enc_wr;
    wire        wr_now;      // write strobe for all five macros
    wire [7:0]  q0, q1, q2, q3, q4;

    wire men = cyc_i | (state != S_IDLE);
    wire ren = issue_rd;

    zirh_sram39_slice u_m0 (.clk(clk), .men(men), .wen(wr_now), .ren(ren),
                            .adr(widx), .d(enc_wr[7:0]),   .q(q0));
    zirh_sram39_slice u_m1 (.clk(clk), .men(men), .wen(wr_now), .ren(ren),
                            .adr(widx), .d(enc_wr[15:8]),  .q(q1));
    zirh_sram39_slice u_m2 (.clk(clk), .men(men), .wen(wr_now), .ren(ren),
                            .adr(widx), .d(enc_wr[23:16]), .q(q2));
    zirh_sram39_slice u_m3 (.clk(clk), .men(men), .wen(wr_now), .ren(ren),
                            .adr(widx), .d(enc_wr[31:24]), .q(q3));
    zirh_sram39_slice u_m4 (.clk(clk), .men(men), .wen(wr_now), .ren(ren),
                            .adr(widx), .d({1'b0, enc_wr[38:32]}), .q(q4));

    // --- decode (valid in the cycle after issue_rd) -------------------------
`ifdef FORMAL
    wire [38:0] raw = {q4[6:0], q3, q2, q1, q0} ^ f_corrupt_i;
`else
    wire [38:0] raw = {q4[6:0], q3, q2, q1, q0};
`endif
    wire [38:1] cw_raw  = raw[37:0];
    wire [5:0]  syn     = syndrome_of(cw_raw);
    wire        ovr_bad = (^cw_raw) ^ raw[38];

    wire correct_cw  = (syn != 6'd0) &  ovr_bad & (syn <= 6'd38);
    wire correct_ovr = (syn == 6'd0) &  ovr_bad;
    wire uncorr      = ((syn != 6'd0) & ~ovr_bad) |
                       ( ovr_bad & (syn > 6'd38));
    wire had_corr    = correct_cw | correct_ovr;

    wire [38:1] cw_fixed = correct_cw ? (cw_raw ^ (38'b1 << (syn - 1)))
                                      : cw_raw;
    wire [38:0] fixed    = {^cw_fixed, cw_fixed};

    wire [37:0] gathered = gather_data_ext(cw_fixed);
    wire [31:0] rd_data  = gathered[31:0];

    // --- merge + write ------------------------------------------------------
    wire [31:0] merged = {sel_i[3] ? dat_i[31:24] : rd_data[31:24],
                          sel_i[2] ? dat_i[23:16] : rd_data[23:16],
                          sel_i[1] ? dat_i[15:8]  : rd_data[15:8],
                          sel_i[0] ? dat_i[7:0]   : rd_data[7:0]};

    // what gets written when wr_now strobes:
    //   IDLE + full write  : encode(dat_i)
    //   S_RD  + we (RMW)   : encode(merged)      (registered into S_WB? no -
    //                        the merge is combinational off the decode, so
    //                        the write happens directly in the decode cycle)
    //   S_RD  + rd + corr  : fixed               (scrub-on-read write-back)
    wire wr_full  = (state == S_IDLE) & cyc_i & ~ack_q & we_i & full_wr;
    wire wr_rmw   = decode_cy & we_i;
    wire wr_scrub = decode_cy & ~we_i & had_corr;

    assign wr_now = wr_full | wr_rmw | wr_scrub;
    assign enc_wr = wr_full ? encode(dat_i)
                  : wr_rmw  ? encode(merged)
                  :           fixed;

    // --- FSM + registered outputs ------------------------------------------
    reg [31:0] rdt_q;
    reg        ack_q;

    always @(posedge clk) begin
        if (!rst_n) begin
            state        <= S_IDLE;
            ack_q        <= 1'b0;
            evt_corr_o   <= 1'b0;
            evt_uncorr_o <= 1'b0;
        end else begin
            ack_q        <= 1'b0;
            evt_corr_o   <= 1'b0;
            evt_uncorr_o <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (wr_full)       ack_q <= 1'b1;
                    else if (issue_rd) state <= S_RD;
                end
                S_RD: begin
                    // decode cycle: data + ack for reads and RMWs; the
                    // scrub or RMW write strobes the port this same
                    // cycle, so IDLE is safe to reenter immediately
                    rdt_q        <= rd_data;
                    ack_q        <= 1'b1;
                    evt_corr_o   <= had_corr;
                    evt_uncorr_o <= uncorr;
                    state        <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end

    assign rdt_o = rdt_q;
    assign ack_o = ack_q;

endmodule

// --- one slice: the PDK macro with BIST tied off -----------------------------
module zirh_sram39_slice (
    input  wire       clk,
    input  wire       men,
    input  wire       wen,
    input  wire       ren,
    input  wire [9:0] adr,
    input  wire [7:0] d,
    output wire [7:0] q
);

    RM_IHPSG13_1P_1024x8_c2_bm_bist u_macro (
        .A_CLK       (clk),
        .A_MEN       (men),
        .A_WEN       (wen),
        .A_REN       (ren),
        .A_ADDR      (adr),
        .A_DIN       (d),
        .A_DLY       (1'b0),
        .A_DOUT      (q),
        .A_BM        (8'hFF),
        .A_BIST_CLK  (1'b0),
        .A_BIST_EN   (1'b0),
        .A_BIST_MEN  (1'b0),
        .A_BIST_WEN  (1'b0),
        .A_BIST_REN  (1'b0),
        .A_BIST_ADDR (10'd0),
        .A_BIST_DIN  (8'd0),
        .A_BIST_BM   (8'd0)
    );

endmodule

`default_nettype wire
