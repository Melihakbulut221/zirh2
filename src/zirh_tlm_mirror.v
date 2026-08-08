// =============================================================================
// ZIRH-2 - telemetry mirror: a CPU-untouchable second serial output
// zirh_tlm_mirror.v
//
// Born from a measured failure: the reboot-storm campaign showed that a
// deranged CPU can flood the shared UART, interleaving garbage with
// telemetry bytes on the one TX line - frames lose atomicity and the
// ground reads nothing until a watchdog reboot (or the zombie-clearing
// voluntary restart) ends the spam. The instrument survived; its VOICE
// did not.
//
// This block is the answer: a transmit-only serial port that snoops the
// telemetry byte handshake upstream of the shared UART and serializes
// every frame byte on its own pin. It sits on no bus, decodes no
// commands, and the CPU cannot address it - the only writer is the
// TMR'd telemetry framer itself. 8N1, idle high, same divisor as the
// main link: one ground-station decoder serves both pins. Electrically
// neutral TTL serial: an RS-232 transceiver (MAX232-class) or an
// RS-422 pair off this pin is a bench choice, not a chip one.
//
// A one-deep holding register absorbs handshake jitter - the primary
// UART itself paces each telemetry byte over ten bit times, so the
// mirror (same baud) always drains in time; on an overrun the incoming
// byte simply overwrites the pending one, freshest-wins with no torn
// characters. If firmware responses stall telemetry on the primary,
// the mirror idles - it mirrors the INSTRUMENT, not the computer.
// Deliberately
// PLAIN flops: this is the backup voice, its failure mode is garbled
// frames on a backup pin (visible, harmless), and after the fit
// campaign every replica has to earn its area.
// =============================================================================

`default_nettype none

module zirh_tlm_mirror #(
    parameter integer DIV = 174        // clocks per bit, matches the UART
) (
    input  wire       clk,
    input  wire       rst_n,

    input  wire [7:0] tlm_data_i,      // the framer's byte stream...
    input  wire       tlm_strobe_i,    // ...latched on each accepted byte

    output wire       tx_o
);

    localparam integer DW = $clog2(DIV);

    // --- one-deep holding register, freshest wins ----------------------------
    reg [7:0] nxt;
    reg       nxt_v;

    // --- serializer: {stop, data[7:0], start} sent LSB first -----------------
    reg [9:0]    shift;
    reg [3:0]    nbits;
    reg [DW-1:0] divq;

    wire busy     = (nbits != 4'd0);
    wire bit_tick = (divq == DIV - 1);
    wire take     = ~busy & nxt_v;

    always @(posedge clk) begin
        if (!rst_n) begin
            nxt    <= 8'h00;
            nxt_v  <= 1'b0;
            shift  <= 10'h3FF;
            nbits  <= 4'd0;
            divq   <= {DW{1'b0}};
        end else begin
            if (tlm_strobe_i) nxt <= tlm_data_i;
            nxt_v <= tlm_strobe_i ? 1'b1 : (take ? 1'b0 : nxt_v);

            if (!busy) begin
                divq <= {DW{1'b0}};
                if (nxt_v) begin
                    shift <= {1'b1, nxt, 1'b0};
                    nbits <= 4'd10;
                end
            end else begin
                divq <= bit_tick ? {DW{1'b0}} : divq + 1'b1;
                if (bit_tick) begin
                    shift <= {1'b1, shift[9:1]};
                    nbits <= nbits - 4'd1;
                end
            end
        end
    end

    assign tx_o = busy ? shift[0] : 1'b1;

endmodule

`default_nettype wire
