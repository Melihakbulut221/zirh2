// =============================================================================
// ZIRH-2 - CAN 2.0A-lite node
// zirh_can.v
//
// A single-node bench link, bit-faithful where the protocol is the
// experiment and ruthless where it is not. Kept: standard data frames
// (SOF, 11-bit ID, RTR, IDE, r0, DLC, one data byte, CRC-15 0x4599,
// CRC delimiter, ACK slot, ACK delimiter, 7-bit EOF, 3-bit intermission),
// bit stuffing SOF..CRC with stuff-error detection, CRC check, the ACK
// handshake (the receiver drives the slot dominant onto the shared
// wired-AND TX line, so an external TX-to-RX loopback acknowledges its
// own beacons exactly as a two-node bus would). Dropped: arbitration
// and retransmission (one node, no contention), overload frames, error
// frame signalling, extended IDs. Fixed bit time (CAN_DIV clocks,
// sampled mid-bit), both ends on the same oscillator by construction.
//
// THE EXPERIMENT, as in zirh_spw: the TX and RX protocol FSMs are TMR
// registers with voted feedback plus safe-state traps - the unreachable
// state encodings fall back to idle/integration instead of wedging, the
// pairing the fault-tolerant-FSM literature recommends. Datapath shift
// registers and the serial CRC are deliberately PLAIN flops: they are
// the beam targets, and a corrupted CRC is precisely what the error
// counter is there to count. Per the standard, the receiver arms only
// after 11 consecutive recessive bits (bus integration) - which also
// keeps a bench with the RX pin tied low silent instead of counting
// garbage forever.
//
// Counters (TMR, saturating, read at 0x3040): TX beacons sent, frames
// received with good CRC and form, errors (stuff, CRC, form, no-ACK).
// =============================================================================

`default_nettype none

module zirh_can #(
    parameter integer CAN_DIV   = 40,      // clocks per bit (500 kb/s at 20 MHz)
    parameter [10:0]  BEACON_ID = 11'h5A5
) (
    input  wire       clk,
    input  wire       rst_n,

    input  wire       rx_i,               // bus level in (1 = recessive)
    output wire       tx_o,               // wired-AND bus drive

    input  wire       beacon_i,           // pulse: transmit one beacon frame
    input  wire [7:0] beacon_data_i,

    output wire [7:0] tx_cnt_o,
    output wire [7:0] rx_ok_cnt_o,
    output wire [7:0] err_cnt_o,
    output reg  [7:0] rx_data_o,          // last good payload byte
    output wire       err_tmr_o
);

    // --- bit clock -----------------------------------------------------------
    localparam integer DW = $clog2(CAN_DIV);
    reg [DW-1:0] divq;
    wire bit_tick    = (divq == CAN_DIV - 1);
    wire sample_tick = (divq == CAN_DIV / 2);
    always @(posedge clk) begin
        if (!rst_n) divq <= {DW{1'b0}};
        else        divq <= bit_tick ? {DW{1'b0}} : divq + 1'b1;
    end

    reg [1:0] rxs;
    always @(posedge clk) begin
        if (!rst_n) rxs <= 2'b11;
        else        rxs <= {rxs[0], rx_i};
    end
    wire rx = rxs[1];

    // =========================================================================
    // TX engine
    // =========================================================================
    localparam [2:0] T_IDLE = 3'd0, T_STUFFED = 3'd1, T_TAIL = 3'd2,
                     T_ACK  = 3'd3, T_EOF     = 3'd4;
                     // 3'd5..7: trap -> T_IDLE

    // frame body SOF..CRC assembled in a shift register, stuffing applied
    // on the way out; the tail (delimiters, EOF, intermission) is fixed
    localparam integer BODYW = 1 + 11 + 1 + 1 + 1 + 4 + 8 + 15;   // 42

    wire [2:0] t_state;
    wire       t_serr;
    reg  [2:0] t_state_d;
    zirh_tmr_reg #(.WIDTH(3)) u_tstate (
        .clk(clk), .rst_n(rst_n), .en_i(1'b1), .d_i(t_state_d),
        .q_o(t_state), .err_o(t_serr));

    reg [BODYW-1:0] t_body;
    reg [5:0]       t_left;      // bits left in the current phase
    reg [3:0]       t_hist;      // {equal-run count, last bit}
    reg             t_out;       // current TX bit (pre wired-AND)
    reg             t_ack_seen;
    reg             ev_tx_done, ev_tx_noack;

    wire        t_bit = t_body[BODYW-1];
    wire        t_stuff_now = (t_hist[3:1] == 3'd5);    // 5 equal sent

    // serial CRC-15 over the unstuffed body as it leaves
    reg [14:0] crc_t;
    wire crc_t_fb = crc_t[14] ^ t_bit;
    reg t_body_crc_phase;

    always @(*) begin
        case (t_state)
            T_IDLE:    t_state_d = (t_go) ? T_STUFFED : T_IDLE;
            T_STUFFED: t_state_d = (bit_tick & (t_left == 6'd1) & ~t_stuff_now
                                    & ~t_body_crc_phase)
                                   ? T_TAIL : T_STUFFED;
            T_TAIL:    t_state_d = (bit_tick & (t_left == 6'd1)) ? T_ACK : T_TAIL;
            T_ACK:     t_state_d = bit_tick ? T_EOF : T_ACK;
            T_EOF:     t_state_d = (bit_tick & (t_left == 6'd1)) ? T_IDLE : T_EOF;
            default:   t_state_d = T_IDLE;      // safe-state trap
        endcase
    end

    // beacon request is latched so a mid-frame pulse is not lost
    reg t_req;
    wire t_go = t_req & (t_state == T_IDLE) & rx_integrated;

    always @(posedge clk) begin
        if (!rst_n) begin
            t_body <= {BODYW{1'b0}};
            t_left <= 6'd0;
            t_hist <= 4'b0011;   // empty: impossible run of 1s
            t_out  <= 1'b1;
            t_req  <= 1'b0;
            t_ack_seen <= 1'b0;
            ev_tx_done  <= 1'b0;
            ev_tx_noack <= 1'b0;
            crc_t <= 15'h0;
            t_body_crc_phase <= 1'b0;
        end else begin
            ev_tx_done  <= 1'b0;
            ev_tx_noack <= 1'b0;
            if (beacon_i) t_req <= 1'b1;

            case (t_state)
                T_IDLE: begin
                    t_out <= 1'b1;
                    if (t_go) begin
                        // SOF(0) ID RTR(0) IDE(0) r0(0) DLC=1 DATA
                        t_body <= {1'b0, BEACON_ID, 1'b0, 1'b0, 1'b0,
                                   4'd1, beacon_data_i, 15'h0};
                        t_left <= 6'd27;          // SOF..DATA, CRC appended
                        t_hist <= 4'b0011;
                        crc_t  <= 15'h0;
                        t_body_crc_phase <= 1'b1;
                        t_req  <= 1'b0;
                    end
                end
                T_STUFFED: if (bit_tick) begin
                    if (t_stuff_now) begin
                        // emit the complement, reset history
                        t_out  <= ~t_hist[0];
                        t_hist <= {3'd1, ~t_hist[0]};
                    end else begin
                        t_out <= t_bit;
                        t_hist <= (t_bit == t_hist[0])
                                  ? {t_hist[3:1] + 3'd1, t_bit}
                                  : {3'd1, t_bit};
                        // CRC over unstuffed bits, spec algorithm
                        crc_t <= crc_t_fb
                                 ? ({crc_t[13:0], 1'b0} ^ 15'h4599)
                                 : {crc_t[13:0], 1'b0};
                        t_body <= {t_body[BODYW-2:0], 1'b0};
                        t_left <= t_left - 6'd1;
                        if (t_left == 6'd1) begin
                            if (t_body_crc_phase) begin
                                // body done: append CRC, stay stuffed
                                t_body[BODYW-1 -: 15] <=
                                    crc_t_fb ? ({crc_t[13:0], 1'b0} ^ 15'h4599)
                                             : {crc_t[13:0], 1'b0};
                                t_left <= 6'd15;
                                t_body_crc_phase <= 1'b0;
                            end
                        end
                    end
                end
                T_TAIL: if (bit_tick) begin        // CRC delimiter
                    t_out  <= 1'b1;
                    t_left <= t_left - 6'd1;
                end
                T_ACK: begin
                    if (divq == {DW{1'b0}}) t_out <= 1'b1;   // release the slot
                    // sample LATE in the slot: the receiver's pull crosses a
                    // two-flop sync plus the bus, and mid-bit misses it by a
                    // cycle on a tight loopback (measured)
                    if (divq == CAN_DIV - 2) t_ack_seen <= ~rx;
                    if (bit_tick) begin
                        t_left <= 6'd11;   // ACKdel + EOF(7) + IFS(3)
                    end
                end
                T_EOF: if (bit_tick) begin
                    t_out  <= 1'b1;
                    t_left <= t_left - 6'd1;
                    if (t_left == 6'd1) begin
                        ev_tx_done  <= 1'b1;
                        ev_tx_noack <= ~t_ack_seen;
                        t_ack_seen  <= 1'b0;
                    end
                end
                default: t_out <= 1'b1;
            endcase
            // entering T_TAIL: one CRC-delimiter bit
            if (t_state == T_STUFFED && t_state_d == T_TAIL) t_left <= 6'd1;
        end
    end

    // =========================================================================
    // RX engine
    // =========================================================================
    localparam [2:0] R_INTEG = 3'd0, R_IDLE = 3'd1, R_BODY = 3'd2,
                     R_TAIL  = 3'd3;
                     // 3'd4..7: trap -> R_INTEG

    wire [2:0] r_state;
    wire       r_serr;
    reg  [2:0] r_state_d;
    zirh_tmr_reg #(.WIDTH(3)) u_rstate (
        .clk(clk), .rst_n(rst_n), .en_i(1'b1), .d_i(r_state_d),
        .q_o(r_state), .err_o(r_serr));

    reg [6:0]  r_nbits;      // unstuffed bits collected in body
    reg [3:0]  r_integ;      // consecutive recessive bits seen
    reg [3:0]  r_hist;       // stuff history: {equal-run count, last}
    reg [3:0]  r_dlc;
    reg [7:0]  r_data;
    reg [14:0] crc_r;
    reg [3:0]  r_tail_left;
    reg        r_ack_drive;  // receiver pulls the ACK slot dominant
    reg        ev_rx_ok, ev_rx_err;

    wire rx_integrated = (r_state != R_INTEG);
    wire r_stuff_bit   = (r_hist[3:1] == 3'd5);    // next bit is a stuff bit
    localparam integer RBODY = 1 + 11 + 1 + 1 + 1 + 4;   // SOF..DLC = 19
    wire crc_r_fb = crc_r[14] ^ rx;

    // body length depends on DLC (data bytes) + 15 CRC bits
    wire [6:0] r_body_len = 7'd19 + {r_dlc[3] ? 4'd8 : r_dlc, 3'b000} + 7'd15;

    always @(*) begin
        case (r_state)
            R_INTEG: r_state_d = (sample_tick & rx & (r_integ == 4'd10))
                                 ? R_IDLE : R_INTEG;
            R_IDLE:  r_state_d = (sample_tick & ~rx) ? R_BODY : R_IDLE;
            R_BODY:  r_state_d = rx_err_now ? R_INTEG
                               : (body_done ? R_TAIL : R_BODY);
            R_TAIL:  r_state_d = (sample_tick & (r_tail_left == 4'd1))
                                 ? R_INTEG : R_TAIL;
            default: r_state_d = R_INTEG;       // safe-state trap
        endcase
    end

    reg rx_err_now, body_done;

    always @(posedge clk) begin
        if (!rst_n) begin
            r_nbits <= 7'd0;
            r_integ <= 4'd0;
            r_hist  <= 4'b0000;
            r_dlc   <= 4'd0;
            r_data  <= 8'h00;
            crc_r   <= 15'h0;
            r_tail_left <= 4'd0;
            r_ack_drive <= 1'b0;
            ev_rx_ok    <= 1'b0;
            ev_rx_err   <= 1'b0;
            rx_err_now  <= 1'b0;
            body_done   <= 1'b0;
            rx_data_o   <= 8'h00;
        end else begin
            ev_rx_ok   <= 1'b0;
            ev_rx_err  <= 1'b0;
            rx_err_now <= 1'b0;
            body_done  <= 1'b0;

            case (r_state)
                R_INTEG: if (sample_tick) begin
                    r_integ <= rx ? (r_integ + 4'd1) : 4'd0;
                end
                R_IDLE: if (sample_tick & ~rx) begin
                    // SOF seen; SOF=0 with CRC seed 0 leaves the LFSR at 0
                    r_nbits <= 7'd1;
                    r_hist  <= {3'd1, 1'b0};   // SOF consumed: one 0 seen
                    crc_r   <= 15'h0;
                    r_dlc   <= 4'd0;
                end
                R_BODY: if (sample_tick) begin
                    if (r_stuff_bit) begin
                        // stuff bit: must be the complement
                        if (rx == r_hist[0]) begin
                            ev_rx_err  <= 1'b1;    // six equal = stuff error
                            rx_err_now <= 1'b1;
                        end
                        r_hist <= {3'd1, rx};
                    end else begin
                        r_hist <= (rx == r_hist[0])
                                  ? {r_hist[3:1] + 3'd1, rx}
                                  : {3'd1, rx};
                        crc_r <= crc_r_fb
                                 ? ({crc_r[13:0], 1'b0} ^ 15'h4599)
                                 : {crc_r[13:0], 1'b0};
                        // collect DLC and data
                        if (r_nbits >= 6'd15 && r_nbits <= 6'd18)
                            r_dlc <= {r_dlc[2:0], rx};
                        if (r_nbits >= 6'd19 &&
                            r_nbits < 6'd19 + 6'd8 && r_dlc != 4'd0)
                            r_data <= {r_data[6:0], rx};
                        r_nbits <= r_nbits + 7'd1;
                        if (r_nbits == r_body_len - 7'd1) begin
                            // tail bookkeeping: 3 = CRC delimiter bit,
                            // 2 = ACK slot, 1 = ACK delimiter (exit there)
                            body_done   <= 1'b1;
                            r_tail_left <= 4'd3;
                            r_ack_drive <= 1'b0;
                        end
                    end
                end
                R_TAIL: if (sample_tick) begin
                    r_tail_left <= r_tail_left - 4'd1;
                    if (r_tail_left == 4'd2) begin
                        // mid-ACK-slot: the verdict
                        if (crc_ok) begin
                            ev_rx_ok  <= 1'b1;
                            rx_data_o <= r_data;
                        end else
                            ev_rx_err <= 1'b1;
                    end
                end
                default: ;
            endcase

            // ACK drive spans exactly the ACK-slot bit: on at the end of
            // the CRC delimiter (tail 3->2 happened mid-delimiter), off at
            // the end of the slot itself
            if (r_state == R_TAIL && r_tail_left == 4'd2 && bit_tick)
                r_ack_drive <= crc_ok;
            if (r_state == R_TAIL && r_tail_left == 4'd1 && bit_tick)
                r_ack_drive <= 1'b0;
            if (r_state == R_INTEG || r_state == R_IDLE)
                r_ack_drive <= 1'b0;
        end
    end

    wire crc_ok = (crc_r == 15'h0);

    // wired-AND bus: transmitter bit AND the receiver's ACK pull
    assign tx_o = t_out & ~r_ack_drive;

    // =========================================================================
    // counters
    // =========================================================================
    wire [7:0] txc_q, rxc_q, errc_q;
    wire e_t, e_r, e_x;
    zirh_tmr_reg #(.WIDTH(8)) u_txc (
        .clk(clk), .rst_n(rst_n),
        .en_i(ev_tx_done & (txc_q != 8'hFF)),
        .d_i(txc_q + 8'h1), .q_o(txc_q), .err_o(e_t));
    zirh_tmr_reg #(.WIDTH(8)) u_rxc (
        .clk(clk), .rst_n(rst_n),
        .en_i(ev_rx_ok & (rxc_q != 8'hFF)),
        .d_i(rxc_q + 8'h1), .q_o(rxc_q), .err_o(e_r));
    zirh_tmr_reg #(.WIDTH(8)) u_errc (
        .clk(clk), .rst_n(rst_n),
        .en_i((ev_rx_err | ev_tx_noack) & (errc_q != 8'hFF)),
        .d_i(errc_q + 8'h1), .q_o(errc_q), .err_o(e_x));

    assign tx_cnt_o    = txc_q;
    assign rx_ok_cnt_o = rxc_q;
    assign err_cnt_o   = errc_q;
    assign err_tmr_o   = t_serr | r_serr | e_t | e_r | e_x;

endmodule

`default_nettype wire
