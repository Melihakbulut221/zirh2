// =============================================================================
// ZIRH-2 - interface experiment block: CAN-lite + SpaceWire-lite + bus regs
// zirh_ifc.v
//
// Owns the upper half of bus slot 3 (adr[6] = 1; the top splits the slot
// between housekeeping and this block). Both protocol cores live here as
// beam experiments: TMR'd, safe-state-trapped protocol FSMs whose error
// and traffic counters answer over the same UART command path as every
// other instrument.
//
// Register map (word offsets from 0x3040):
//   0x40 CAN_STAT RO  {tx_cnt, err_cnt, rx_ok_cnt, rx_data}
//   0x44 CAN_CTRL WO  bit 0: transmit one beacon; data byte = dat[15:8]
//   0x48 SPW_STAT RO  {rx_char, err_cnt, null_cnt, 5'b0, state}
//   0x4C SPW_CTRL RW  bit 0: link enable (level, TMR'd);
//                     bit 1: queue one data char, char = dat[15:8]
// =============================================================================

`default_nettype none

module zirh_ifc #(
    parameter integer CAN_DIV = 40,
    parameter integer SPW_DIV = 4,
    parameter integer SPW_T_RESET = 32,
    parameter integer SPW_T_WAIT  = 64,
    parameter integer SPW_T_CONN  = 64,
    parameter integer SPW_T_DISC  = 8
) (
    input  wire        clk,
    input  wire        rst_n,

    // bus slave (slot 3, adr[6] = 1)
    input  wire        cyc_i,
    input  wire [31:0] adr_i,
    input  wire [31:0] dat_i,
    input  wire        we_i,
    output wire [31:0] rdt_o,
    output wire        ack_o,

    // pins
    input  wire        can_rx_i,
    output wire        can_tx_o,
    input  wire        spw_din_i,
    input  wire        spw_sin_i,
    output wire        spw_dout_o,
    output wire        spw_sout_o,

    output wire        err_tmr_o
);

    wire [1:0] reg_sel = adr_i[3:2];
    wire wr = cyc_i & we_i;
    wire wr_can = wr & (reg_sel == 2'b01);
    wire wr_spw = wr & (reg_sel == 2'b11);

    // one-shot strobes (bus writes last 2 cycles)
    reg can_seen, spw_seen;
    always @(posedge clk) begin
        if (!rst_n) begin
            can_seen <= 1'b0;
            spw_seen <= 1'b0;
        end else begin
            can_seen <= wr_can;
            spw_seen <= wr_spw;
        end
    end
    wire can_beacon = wr_can & ~can_seen & dat_i[0];
    wire spw_send   = wr_spw & ~spw_seen & dat_i[1];

    // link enable is a level, so it gets a TMR register
    wire link_en;
    wire link_err;
    zirh_tmr_reg #(.WIDTH(1)) u_len (
        .clk(clk), .rst_n(rst_n),
        .en_i(wr_spw & ~spw_seen),
        .d_i(dat_i[0]), .q_o(link_en), .err_o(link_err));

    // --- CAN -----------------------------------------------------------------
    wire [7:0] can_txc, can_rxc, can_errc, can_rxd;
    wire       can_err_tmr;

    zirh_can #(.CAN_DIV(CAN_DIV)) u_can (
        .clk(clk), .rst_n(rst_n),
        .rx_i(can_rx_i), .tx_o(can_tx_o),
        .beacon_i(can_beacon), .beacon_data_i(dat_i[15:8]),
        .tx_cnt_o(can_txc), .rx_ok_cnt_o(can_rxc), .err_cnt_o(can_errc),
        .rx_data_o(can_rxd), .err_tmr_o(can_err_tmr));

    // --- SpaceWire -----------------------------------------------------------
    wire [2:0] spw_state;
    wire [7:0] spw_nulls, spw_errs, spw_rxc;
    wire       spw_rxv, spw_err_tmr;

    zirh_spw #(
        .SPW_DIV(SPW_DIV), .T_RESET(SPW_T_RESET), .T_WAIT(SPW_T_WAIT),
        .T_CONN(SPW_T_CONN), .T_DISC(SPW_T_DISC)
    ) u_spw (
        .clk(clk), .rst_n(rst_n),
        .din_i(spw_din_i), .sin_i(spw_sin_i),
        .dout_o(spw_dout_o), .sout_o(spw_sout_o),
        .link_en_i(link_en),
        .tx_char_i(dat_i[15:8]), .tx_char_v_i(spw_send),
        .rx_char_o(spw_rxc), .rx_char_v_o(spw_rxv),
        .state_o(spw_state), .null_cnt_o(spw_nulls), .err_cnt_o(spw_errs),
        .err_tmr_o(spw_err_tmr));

    // rx char valid pulse is consumed by reading SPW_STAT; keep it simple:
    // the register always shows the last received char
    wire _unused = spw_rxv;

    // --- readback ------------------------------------------------------------
    assign rdt_o =
        (reg_sel == 2'b00) ? {can_txc, can_errc, can_rxc, can_rxd} :
        (reg_sel == 2'b10) ? {spw_rxc, spw_errs, spw_nulls, 5'b0, spw_state} :
        32'h0;

    assign ack_o = cyc_i;
    assign err_tmr_o = can_err_tmr | spw_err_tmr | link_err;

endmodule

`default_nettype wire
