// ZIRH-2 - torture harness: zirh_soc alone, UART pins out, slot 3 tied
// (acks immediately, reads zero) so random programs cannot bus-timeout
// on the instrument window they never meaningfully use.
`default_nettype none
`timescale 1ns / 1ps

module tb_torture #(
    parameter ROM_HEX = "torture.hex",
    parameter RESET_DIV = 8
) (
    input  wire clk,
    input  wire rst_n,
    output wire uart_tx
);
    wire        s3_cyc, s3_we;
    wire [31:0] s3_adr, s3_dat;

    zirh_soc #(
        .ROM_HEX   (ROM_HEX),
        .RESET_DIV (RESET_DIV)
    ) u_soc (
        .clk               (clk),
        .rst_n             (rst_n),
        .por_rst_n_i       (rst_n),
        .isp_hold_i        (1'b0),
        .boot_sel_i        (1'b0),
        .isp_cyc_i         (1'b0),
        .isp_adr_i         (32'h0),
        .isp_dat_i         (32'h0),
        .isp_we_i          (1'b0),
        .isp_rdt_o         (),
        .isp_ack_o         (),
        .uart_tx_o         (uart_tx),
        .uart_rx_i         (1'b1),
        .tlm_data_i        (8'h0),
        .tlm_valid_i       (1'b0),
        .tlm_ready_o       (),
        .s3_cyc_o          (s3_cyc),
        .s3_adr_o          (s3_adr),
        .s3_dat_o          (s3_dat),
        .s3_we_o           (s3_we),
        .s3_rdt_i          (32'h0),
        .s3_ack_i          (s3_cyc),
        .evt_bus_timeout_o (),
        .evt_ecc_corr_o    (),
        .evt_ecc_uncorr_o  (),
        .rx_ferr_o         (),
        .err_o             ()
    );

    wire _unused = &{s3_adr, s3_dat, s3_we, 1'b0};
endmodule

`default_nettype wire
