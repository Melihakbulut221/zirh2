// =============================================================================
// ZIRH-2 - SpaceWire-lite link (ECSS-E-ST-50-12C subset)
// zirh_spw.v
//
// A single-lane Data-Strobe link small enough to live on the tile and
// honest enough to be a real experiment: the full six-state link FSM
// (ErrorReset, ErrorWait, Ready, Started, Connecting, Run), NULL/FCT
// exchange, data characters with the standard's spanning odd parity,
// parity/escape/disconnect error detection - and nothing else: no
// time-codes, no credit accounting beyond the connect handshake, no
// packets (a data char IS the payload). Both ends of the bench link run
// from the same oscillator, so the receiver samples through a two-flop
// synchronizer and recovers bits from D-XOR-S transitions without a
// clock-recovery PLL; the TX bit period (SPW_DIV clocks) must be at
// least 4 for that to hold.
//
// THE EXPERIMENT: the link FSM state is the classic beam victim of the
// fault-tolerant FSM literature - here it is a TMR register with voted
// feedback (single-replica hits heal in a cycle, counted by the top's
// mismatch detector) PLUS the safe-state trap the literature pairs with
// it: the 3-bit state space has two encodings no legal transition
// reaches, and landing there (a double-replica hit - beyond TMR by
// definition) falls into ErrorReset on the next cycle instead of
// wedging. ErrorReset is the state the standard itself designates as
// the recovery point; the trap makes it the recovery point for
// radiation as well as protocol errors. Error and NULL counters are
// TMR'd and read over the bus (0x3048).
//
// Timers are in TX bit periods and parameterized: at the standard's
// 10 Mbit/s init rate the spec values are 6.4 us and 12.8 us; the
// defaults here scale those to the 5 Mbit/s the 20 MHz system clock
// yields at SPW_DIV=4. Simulation overrides shrink them.
// =============================================================================

`default_nettype none

module zirh_spw #(
    parameter integer SPW_DIV  = 4,    // clocks per TX bit, >= 4
    parameter integer T_RESET  = 32,   // ErrorReset hold, bit periods
    parameter integer T_WAIT   = 64,   // ErrorWait hold, bit periods
    parameter integer T_CONN   = 64,   // Started/Connecting timeout
    parameter integer T_DISC   = 8     // Run: silence -> disconnect
) (
    input  wire       clk,
    input  wire       rst_n,

    input  wire       din_i,
    input  wire       sin_i,
    output reg        dout_o,
    output reg        sout_o,

    input  wire       link_en_i,       // level: try to reach Run
    input  wire [7:0] tx_char_i,
    input  wire       tx_char_v_i,     // pulse: queue one data char
    output reg  [7:0] rx_char_o,
    output reg        rx_char_v_o,     // pulse

    output wire [2:0] state_o,
    output wire [7:0] null_cnt_o,
    output wire [7:0] err_cnt_o,
    output wire       err_tmr_o        // own TMR mismatch, pulse
);

    // --- link FSM encoding (two illegal codes = the safe-state trap) --------
    localparam [2:0] S_ERRRST  = 3'd0,
                     S_ERRWAIT = 3'd1,
                     S_READY   = 3'd2,
                     S_STARTED = 3'd3,
                     S_CONNECT = 3'd4,
                     S_RUN     = 3'd5;   // 3'd6, 3'd7: trap -> S_ERRRST

    // --- TX bit clock --------------------------------------------------------
    localparam integer DW = $clog2(SPW_DIV);
    reg [DW-1:0] divq;
    wire bit_tick = (divq == SPW_DIV - 1);
    always @(posedge clk) begin
        if (!rst_n) divq <= {DW{1'b0}};
        else        divq <= bit_tick ? {DW{1'b0}} : divq + 1'b1;
    end

    // --- RX: synchronize, recover bits from D^S transitions ------------------
    reg [1:0] dsync, ssync;
    always @(posedge clk) begin
        if (!rst_n) begin
            dsync <= 2'b00;
            ssync <= 2'b00;
        end else begin
            dsync <= {dsync[0], din_i};
            ssync <= {ssync[0], sin_i};
        end
    end
    wire rx_d  = dsync[1];
    reg  xor_r;
    wire rx_edge = (dsync[1] ^ ssync[1]) != xor_r;
    always @(posedge clk) begin
        if (!rst_n) xor_r <= 1'b0;
        else        xor_r <= dsync[1] ^ ssync[1];
    end

    // --- RX character assembly ----------------------------------------------
    // SpaceWire chars, first bit = parity, second = flag:
    //   flag 0: data char, 8 more bits LSB first        (10 bits)
    //   flag 1: control char, 2 more bits               (4 bits)
    //     00 FCT   01 EOP   10 EEP   11 ESC
    // NULL = ESC then FCT. The parity bit covers the bits of the PREVIOUS
    // character (after its parity+flag) plus the current parity and flag,
    // odd overall - the standard's spanning parity, kept bit-exact here.
    reg [3:0] rx_nbits;
    reg [9:0] rx_shift;
    reg       rx_flag;
    reg       par_acc;       // parity over the current char's payload bits
    reg       par_hold;      // payload(N-1) ^ p(N), awaiting the flag
    reg       rx_esc;        // previous control char was ESC
    reg       rx_got_time;   // any edge since state entry (for disconnect)

    wire [1:0] rx_ctl  = {rx_shift[9], rx_shift[8]};   // MSB-first ctl bits
    wire       rx_is_null = rx_esc & (rx_ctl == 2'b00);

    // events, one clk pulse each
    reg ev_null, ev_fct, ev_dchar, ev_perr, ev_eerr;
    reg [7:0] rx_data_b;

    integer i;
    always @(posedge clk) begin
        if (!rst_n) begin
            rx_nbits    <= 4'd0;
            rx_shift    <= 10'd0;
            rx_flag     <= 1'b0;
            par_acc     <= 1'b0;
            rx_esc      <= 1'b0;
            ev_null     <= 1'b0;
            ev_fct      <= 1'b0;
            ev_dchar    <= 1'b0;
            ev_perr     <= 1'b0;
            ev_eerr     <= 1'b0;
            rx_data_b   <= 8'h00;
            rx_got_time <= 1'b0;
            par_hold    <= 1'b0;
        end else begin
            ev_null  <= 1'b0;
            ev_fct   <= 1'b0;
            ev_dchar <= 1'b0;
            ev_perr  <= 1'b0;
            ev_eerr  <= 1'b0;
            if (rx_edge) begin
                rx_got_time <= 1'b1;
                if (rx_nbits == 4'd0) begin
                    // parity bit: hold payload(N-1)^p, judged at the flag
                    par_hold <= par_acc ^ rx_d;
                    par_acc  <= 1'b0;
                    rx_nbits <= 4'd1;
                end else if (rx_nbits == 4'd1) begin
                    // flag bit closes the spanning window: odd overall
                    if ((par_hold ^ rx_d) == 1'b0)
                        ev_perr <= 1'b1;
                    rx_flag  <= rx_d;
                    rx_nbits <= 4'd2;
                    rx_shift <= 10'd0;
                end else begin
                    par_acc <= par_acc ^ rx_d;
                    if (rx_flag) begin
                        // control char: collect 2 bits MSB first
                        rx_shift <= {rx_shift[8:0], rx_d};
                        if (rx_nbits == 4'd3) begin
                            rx_nbits <= 4'd0;
                            case ({rx_shift[0], rx_d})
                                2'b00: begin           // FCT (or NULL tail)
                                    if (rx_esc) ev_null <= 1'b1;
                                    else        ev_fct  <= 1'b1;
                                    rx_esc <= 1'b0;
                                end
                                2'b11: begin           // ESC
                                    if (rx_esc) ev_eerr <= 1'b1;  // ESC ESC
                                    rx_esc <= 1'b1;
                                end
                                default: begin         // EOP/EEP after ESC?
                                    if (rx_esc) ev_eerr <= 1'b1;
                                    rx_esc <= 1'b0;
                                end
                            endcase
                        end else
                            rx_nbits <= rx_nbits + 4'd1;
                    end else begin
                        // data char: 8 bits LSB first
                        rx_shift <= {rx_shift[8:0], rx_d};
                        if (rx_nbits == 4'd9) begin
                            rx_nbits <= 4'd0;
                            if (rx_esc) ev_eerr <= 1'b1;  // data after ESC
                            else begin
                                ev_dchar <= 1'b1;
                                for (i = 0; i < 8; i = i + 1)
                                    rx_data_b[i] <= (i == 7) ? rx_d
                                                  : rx_shift[6 - i];
                            end
                            rx_esc <= 1'b0;
                        end else
                            rx_nbits <= rx_nbits + 4'd1;
                    end
                end
            end
            if (clr_rx_time) rx_got_time <= 1'b0;
        end
    end

    // --- TX: NULLs, FCT, one queued data char --------------------------------
    // tx_shift holds {bits}; parity computed with the same spanning rule.
    reg [9:0] tx_shift;
    reg [3:0] tx_nbits;
    reg       tx_par;        // parity accumulated over sent payload bits
    reg       tx_pending_d;  // a data char is queued
    reg [7:0] tx_char_q;
    reg       tx_run_fct;    // one FCT owed at Run entry

    wire tx_active = (tx_nbits != 4'd0);
    wire in_tx_states = (state_q == S_STARTED) | (state_q == S_CONNECT) |
                        (state_q == S_RUN);

    // what to send next: Started -> NULL; Connecting -> FCT then NULLs;
    // Run -> queued data char, else NULL
    // A char is loaded as {payload bits MSB..LSB, flag, parity-place}
    // and shifted out LSB-of-time first: parity, flag, then payload.
    reg [1:0] tx_sel;        // 0 NULL(ESC), 1 NULL(FCT tail), 2 FCT, 3 data
    reg       b;             // the bit leaving this period
    always @(posedge clk) begin
        if (!rst_n) begin
            tx_shift     <= 10'd0;
            tx_nbits     <= 4'd0;
            tx_par       <= 1'b0;
            tx_pending_d <= 1'b0;
            tx_char_q    <= 8'h00;
            tx_run_fct   <= 1'b0;
            tx_sel       <= 2'd0;
            dout_o       <= 1'b0;
            sout_o       <= 1'b0;
        end else begin
            // queue in ANY state: a char written together with link
            // enable (the firmware's 'w') waits for Run and goes then
            if (tx_char_v_i) begin
                tx_pending_d <= 1'b1;
                tx_char_q    <= tx_char_i;
            end
            if (state_q == S_CONNECT && state_prev != S_CONNECT)
                tx_run_fct <= 1'b1;

            if (!in_tx_states) begin
                tx_nbits <= 4'd0;
                tx_par   <= 1'b0;
                tx_sel   <= 2'd0;
                // lines quiet in ErrorReset and the wait states
                dout_o   <= 1'b0;
                sout_o   <= (state_q == S_ERRRST) ? 1'b0 : sout_o;
            end else if (bit_tick) begin
                if (!tx_active) begin
                    // choose the next character
                    if (tx_sel == 2'd0) begin
                        // just sent nothing or finished a pair: pick
                        if (state_q == S_CONNECT && tx_run_fct) begin
                            tx_shift <= {8'b0, 2'b00};       // FCT bits
                            tx_nbits <= 4'd4;
                            tx_sel   <= 2'd2;
                        end else if (state_q == S_RUN && tx_pending_d) begin
                            tx_shift <= {tx_char_q, 1'b0, 1'b0};
                            tx_nbits <= 4'd10;
                            tx_sel   <= 2'd3;
                        end else begin
                            tx_shift <= {8'b0, 2'b11};       // ESC bits
                            tx_nbits <= 4'd4;
                            tx_sel   <= 2'd1;                // NULL part 1
                        end
                    end
                end else begin
                    // send one bit: positions are parity, flag, payload...
                    if (tx_nbits == ((tx_sel == 2'd3) ? 4'd10 : 4'd4)) begin
                        // parity bit: odd over prev payload + this p + flag
                        b = ~(tx_par ^ ((tx_sel == 2'd3) ? 1'b0 : 1'b1));
                        tx_par = 1'b0;
                    end else if (tx_nbits == ((tx_sel == 2'd3) ? 4'd9 : 4'd3)) begin
                        b = (tx_sel == 2'd3) ? 1'b0 : 1'b1;   // flag
                    end else begin
                        // payload: data LSB first / ctl bits MSB first
                        if (tx_sel == 2'd3)
                            b = tx_char_q[4'd8 - tx_nbits];
                        else
                            b = tx_shift[tx_nbits - 4'd1];
                        tx_par = tx_par ^ b;
                    end
                    // DS encode: strobe toggles when data does not change
                    if (b == dout_o) sout_o <= ~sout_o;
                    dout_o   <= b;
                    tx_nbits <= tx_nbits - 4'd1;
                    if (tx_nbits == 4'd1) begin
                        if (tx_sel == 2'd1) begin
                            // NULL: ESC sent, now owe the FCT tail
                            tx_shift <= {8'b0, 2'b00};
                            tx_nbits <= 4'd4;
                            tx_sel   <= 2'd0;   // FCT tail then re-choose
                        end else begin
                            if (tx_sel == 2'd2) tx_run_fct   <= 1'b0;
                            if (tx_sel == 2'd3) tx_pending_d <= 1'b0;
                            tx_sel <= 2'd0;
                        end
                    end
                end
            end
        end
    end

    // --- timers (in bit periods) ---------------------------------------------
    localparam integer TW = 12;
    reg [TW-1:0] timer;
    wire timer_z = (timer == {TW{1'b0}});
    reg  clr_rx_time;

    // --- the link FSM: TMR state + safe-state trap ---------------------------
    wire [2:0] state_q;
    wire       state_err;
    reg  [2:0] state_d;
    reg  [2:0] state_prev;

    zirh_tmr_reg #(.WIDTH(3)) u_state (
        .clk(clk), .rst_n(rst_n), .en_i(1'b1), .d_i(state_d),
        .q_o(state_q), .err_o(state_err));

    wire rx_err = ev_perr | ev_eerr;
    wire disconnected = (state_q == S_RUN) & timer_z & ~rx_got_time;

    always @(*) begin
        case (state_q)
            S_ERRRST:  state_d = timer_z ? S_ERRWAIT : S_ERRRST;
            S_ERRWAIT: state_d = rx_err ? S_ERRRST
                               : (timer_z ? S_READY : S_ERRWAIT);
            S_READY:   state_d = rx_err ? S_ERRRST
                               : (link_en_i ? S_STARTED : S_READY);
            S_STARTED: state_d = (rx_err | timer_z) ? S_ERRRST
                               : (ev_null ? S_CONNECT : S_STARTED);
            S_CONNECT: state_d = (rx_err | timer_z) ? S_ERRRST
                               : (ev_fct ? S_RUN : S_CONNECT);
            S_RUN:     state_d = (rx_err | disconnected | ~link_en_i)
                               ? S_ERRRST : S_RUN;
            default:   state_d = S_ERRRST;   // the trap: illegal -> recovery
        endcase
    end

    always @(posedge clk) begin
        if (!rst_n) begin
            timer       <= T_RESET[TW-1:0];
            state_prev  <= S_ERRRST;
            clr_rx_time <= 1'b0;
        end else begin
            state_prev  <= state_q;
            clr_rx_time <= 1'b0;
            // reload on the edge ENTERING the new state (keyed on state_d):
            // keying on the arrival leaves the stale expired timer visible
            // for one cycle and the new state times out instantly (measured)
            if (state_d != state_q) begin
                case (state_d)
                    S_ERRRST:  timer <= T_RESET[TW-1:0];
                    S_ERRWAIT: timer <= T_WAIT[TW-1:0];
                    S_STARTED: timer <= T_CONN[TW-1:0];
                    S_CONNECT: timer <= T_CONN[TW-1:0];
                    S_RUN:     timer <= T_DISC[TW-1:0];
                    default:   timer <= {TW{1'b0}};
                endcase
                clr_rx_time <= 1'b1;
            end else if (bit_tick & ~timer_z) begin
                timer <= timer - 1'b1;
                // Run: any traffic re-arms the disconnect timer
                if (state_q == S_RUN & rx_got_time) begin
                    timer       <= T_DISC[TW-1:0];
                    clr_rx_time <= 1'b1;
                end
            end
        end
    end

    // --- counters and char delivery ------------------------------------------
    wire [7:0] nulls_q, errs_q;
    wire e_n, e_e;
    zirh_tmr_reg #(.WIDTH(8)) u_nulls (
        .clk(clk), .rst_n(rst_n),
        .en_i(ev_null & (nulls_q != 8'hFF)),
        .d_i(nulls_q + 8'h1), .q_o(nulls_q), .err_o(e_n));
    zirh_tmr_reg #(.WIDTH(8)) u_errs (
        .clk(clk), .rst_n(rst_n),
        .en_i((rx_err | disconnected) & (errs_q != 8'hFF)),
        .d_i(errs_q + 8'h1), .q_o(errs_q), .err_o(e_e));

    always @(posedge clk) begin
        if (!rst_n) begin
            rx_char_o   <= 8'h00;
            rx_char_v_o <= 1'b0;
        end else begin
            rx_char_v_o <= 1'b0;
            if (ev_dchar & (state_q == S_RUN)) begin
                rx_char_o   <= rx_data_b;
                rx_char_v_o <= 1'b1;
            end
        end
    end

    assign state_o    = state_q;
    assign null_cnt_o = nulls_q;
    assign err_cnt_o  = errs_q;
    assign err_tmr_o  = state_err | e_n | e_e;

endmodule

`default_nettype wire
