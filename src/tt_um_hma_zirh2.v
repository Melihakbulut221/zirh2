// =============================================================================
// ZIRH-2 - top level (8x2 tile candidate)
// tt_um_hma_zirh2.v
//
// clk_rst (reused from ZIRH-1 verbatim) + the SoC cluster + the housekeeping
// block + telemetry v2. Control that ZIRH-1 needed pins for now flows over
// the UART command path through the CPU; the pins that remain are the ones
// that must work when the CPU does not. PIN MAP FROZEN 2026-08-07 - the
// authoritative table lives in docs/ZIRH2-PINMAP.md and info-zirh2.yaml;
// changes there and here move together or not at all:
//
//   ui[3]  UART_RX      (same position as ZIRH-1 - one bench cable)
//   uo[0]  HEARTBEAT    clk_rst alive, ~1.2 Hz at 20 MHz
//   uo[1]  CPU_ALIVE    toggles on every firmware signature write - a dead
//                       CPU freezes this pin while HEARTBEAT keeps blinking:
//                       the instrument/computer failure separation, visible
//                       on two LEDs
//   uo[2]  SEU_EVT      any monitor ring event, scope the beam live
//   uo[3]  ERR_TMR      any TMR replica mismatch anywhere on the die
//   uo[4]  UART_TX      telemetry v2 + firmware responses
//   uo[5]  ECC_EVT      ECC RAM corrected/uncorrected event
//   uo[6]  BUS_TIMEOUT  bus watchdog fired (firmware touched a dead slot)
//   uo[7]  ARMED        monitor warm-up done
//   uio[0] CAN_RX      in   CAN bus level (1 = recessive); bench loopback
//   uio[1] CAN_TX      out  wired-AND CAN drive (beacons + RX ACK pull)
//   uio[2] SPW_DIN     in   SpaceWire data in
//   uio[3] SPW_SIN     in   SpaceWire strobe in
//   uio[4] SPW_DOUT    out  SpaceWire data out
//   uio[5] SPW_SOUT    out  SpaceWire strobe out
//   uio[6] -           in   unused (reserved)
//   uio[7] TLM_MIRROR  out  CPU-untouchable telemetry mirror, 8N1 TTL
//                           serial (RS-232/RS-422 by bench transceiver)
// =============================================================================

`default_nettype none

module tt_um_hma_zirh2 #(
    parameter ROM_HEX = "",
    parameter INTERVAL_LOG2 = 16,
    parameter RESET_DIV = 174,
    parameter WD_LIMIT_LOG2 = 20,
    parameter CAN_DIV = 40,
    parameter SPW_DIV = 4,
    parameter SPW_T_RESET = 32,
    parameter SPW_T_WAIT  = 64,
    parameter SPW_T_CONN  = 64,
    parameter SPW_T_DISC  = 8
) (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

  wire rst_n_sys, heartbeat, tick16, tick256, err_hb;

  zirh_clk_rst #(.HB_BIT(23)) u_clk_rst (
      .clk(clk), .rst_n_pad(rst_n),
      .rst_n_o(rst_n_sys), .heartbeat_o(heartbeat),
      .tick_div16_o(tick16), .tick_div256_o(tick256), .err_hb_o(err_hb));

  // --- SoC ------------------------------------------------------------------
  wire [7:0]  tlm_data;
  wire        tlm_valid, tlm_ready;
  wire        s3_cyc, s3_we;
  wire [31:0] s3_adr, s3_dat, s3_rdt;
  wire        s3_ack;
  wire        evt_bus_to, evt_corr, evt_uncorr, rx_ferr, err_soc;
  wire        uart_tx;

  // The CPU watchdog resets ONLY the SoC: the instrument (hk, tlm) and
  // clk_rst never see it, so telemetry keeps flowing across a reboot and
  // the BOOT field counts it.
  wire wd_rst;
  wire soc_rst_n = rst_n_sys & ~wd_rst;

  zirh_soc #(
      .ROM_HEX   (ROM_HEX),
      .RESET_DIV (RESET_DIV)
  ) u_soc (
      .clk               (clk),
      .rst_n             (soc_rst_n),
      .uart_tx_o         (uart_tx),
      .uart_rx_i         (ui_in[3]),
      .tlm_data_i        (tlm_data),
      .tlm_valid_i       (tlm_valid),
      .tlm_ready_o       (tlm_ready),
      .s3_cyc_o          (s3_cyc),
      .s3_adr_o          (s3_adr),
      .s3_dat_o          (s3_dat),
      .s3_we_o           (s3_we),
      .s3_rdt_i          (s3_rdt),
      .s3_ack_i          (s3_ack),
      .evt_bus_timeout_o (evt_bus_to),
      .evt_ecc_corr_o    (evt_corr),
      .evt_ecc_uncorr_o  (evt_uncorr),
      .rx_ferr_o         (rx_ferr),
      .err_o             (err_soc)
  );

  // --- housekeeping (slot 3) ------------------------------------------------
  wire [15:0] c_plain, c_raw_a, c_esc_a, c_raw_b, c_esc_b;
  wire [7:0]  c_ecc_c, c_ecc_u, cpu_sig, boot_cnt, c_busto, c_ferr;
  wire [1:0]  hk_mode;
  wire        hk_armed, hk_infra, hk_evt, cpu_alive;

  wire s3_ifc   = s3_adr[6];
  wire [31:0] hk_rdt, ifc_rdt;
  wire hk_ack, ifc_ack;
  assign s3_rdt = s3_ifc ? ifc_rdt : hk_rdt;
  assign s3_ack = s3_ifc ? ifc_ack : hk_ack;

  zirh_hk #(.WD_LIMIT_LOG2(WD_LIMIT_LOG2)) u_hk (
      .clk          (clk),
      .rst_n        (rst_n_sys),
      .cyc_i        (s3_cyc & ~s3_ifc),
      .adr_i        (s3_adr),
      .dat_i        (s3_dat),
      .we_i         (s3_we),
      .rdt_o        (hk_rdt),
      .ack_o        (hk_ack),
      .ecc_corr_i   (evt_corr),
      .ecc_uncorr_i (evt_uncorr),
      .bus_to_i     (evt_bus_to),
      .rx_ferr_i    (rx_ferr),
      .cnt_plain_o  (c_plain),
      .cnt_raw_a_o  (c_raw_a),
      .cnt_esc_a_o  (c_esc_a),
      .cnt_raw_b_o  (c_raw_b),
      .cnt_esc_b_o  (c_esc_b),
      .cnt_ecc_c_o  (c_ecc_c),
      .cnt_ecc_u_o  (c_ecc_u),
      .cnt_bus_to_o (c_busto),
      .cnt_ferr_o   (c_ferr),
      .boot_cnt_o   (boot_cnt),
      .cpu_sig_o    (cpu_sig),
      .mode_o       (hk_mode),
      .armed_o      (hk_armed),
      .err_infra_o  (hk_infra),
      .evt_o        (hk_evt),
      .cpu_alive_o  (cpu_alive),
      .wd_rst_o     (wd_rst),
      .env_ro_i     (env_ro_word),
      .env_sb_i     (env_sb_word),
      .env_start_o  (env_start),
      .env_test_o   (env_test),
      .clear_o      (hk_clear)
  );

  // --- interface experiments (slot 3 upper half) ----------------------------
  wire can_tx, spw_dout, spw_sout, err_ifc;

  zirh_ifc #(
      .CAN_DIV(CAN_DIV), .SPW_DIV(SPW_DIV),
      .SPW_T_RESET(SPW_T_RESET), .SPW_T_WAIT(SPW_T_WAIT),
      .SPW_T_CONN(SPW_T_CONN), .SPW_T_DISC(SPW_T_DISC)
  ) u_ifc (
      .clk       (clk),
      .rst_n     (rst_n_sys),
      .cyc_i     (s3_cyc & s3_ifc),
      .adr_i     (s3_adr),
      .dat_i     (s3_dat),
      .we_i      (s3_we),
      .rdt_o     (ifc_rdt),
      .ack_o     (ifc_ack),
      .can_rx_i  (uio_in[0]),
      .can_tx_o  (can_tx),
      .spw_din_i (uio_in[2]),
      .spw_sin_i (uio_in[3]),
      .spw_dout_o(spw_dout),
      .spw_sout_o(spw_sout),
      .err_tmr_o (err_ifc)
  );

  // --- environment monitor (TID oscillator, SET catcher, burst) ------------
  wire [31:0] env_ro_word, env_sb_word;
  wire        env_start, env_test, hk_clear, err_env;

  zirh_env u_env (
      .clk       (clk),
      .rst_n     (rst_n_sys),
      .start_i   (env_start),
      .test_i    (env_test),
      .clear_i   (hk_clear),
      .evt_i     (hk_evt),
      .ro_word_o (env_ro_word),
      .sb_word_o (env_sb_word),
      .err_o     (err_env)
  );

  // --- telemetry v2 ---------------------------------------------------------
  wire err_tlm;

  zirh_tlm2 #(.INTERVAL_LOG2(INTERVAL_LOG2)) u_tlm (
      .clk         (clk),
      .rst_n       (rst_n_sys),
      .cnt_plain_i (c_plain),
      .cnt_raw_a_i (c_raw_a),
      .cnt_esc_a_i (c_esc_a),
      .cnt_raw_b_i (c_raw_b),
      .cnt_esc_b_i (c_esc_b),
      .cnt_ecc_c_i (c_ecc_c),
      .cnt_ecc_u_i (c_ecc_u),
      .cpu_sig_i   (cpu_sig),
      .boot_cnt_i  (boot_cnt),
      .cnt_bus_to_i(c_busto),
      .cnt_ferr_i  (c_ferr),
      .armed_i     (hk_armed),
      .mode_i      (hk_mode),
      .err_infra_i (hk_infra),
      .tx_data_o   (tlm_data),
      .tx_valid_o  (tlm_valid),
      .tx_ready_i  (tlm_ready),
      .err_o       (err_tlm)
  );

  // --- telemetry mirror: the flood-proof second voice -----------------------
  wire mirror_tx;

  zirh_tlm_mirror #(.DIV(RESET_DIV)) u_mirror (
      .clk          (clk),
      .rst_n        (rst_n_sys),
      .tlm_data_i   (tlm_data),
      .tlm_strobe_i (tlm_valid & tlm_ready),
      .tx_o         (mirror_tx)
  );

  // --- pins -----------------------------------------------------------------
  reg cpu_alive_tgl;
  always @(posedge clk) begin
    if (!rst_n_sys)     cpu_alive_tgl <= 1'b0;
    else if (cpu_alive) cpu_alive_tgl <= ~cpu_alive_tgl;
  end

  wire err_any = err_hb | err_soc | err_tlm | hk_infra | err_env | err_ifc;

  assign uo_out = {hk_armed, evt_bus_to, evt_corr | evt_uncorr, uart_tx,
                   err_any, hk_evt, cpu_alive_tgl, heartbeat};

  assign uio_out = {mirror_tx, 1'b0, spw_sout, spw_dout, 1'b0, 1'b0, can_tx, 1'b0};
  assign uio_oe  = 8'b1011_0010;

  wire _unused = &{ena, ui_in[7:4], ui_in[2:0], uio_in[7:6],
                   uio_in[5:4], uio_in[1], tick16, tick256, 1'b0};

endmodule

`default_nettype wire
