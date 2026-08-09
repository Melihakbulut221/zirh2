// =============================================================================
// ZIRH-2 - mask ROM: 1 KB firmware, synthesized constants
// zirh_rom.v
//
// 256 x 32-bit words. Default contents come from src/rom_init.vh, a
// GENERATED include committed next to this file (fw/rom_gen.py emits it
// from the CI firmware build) - so every consumer of the RTL, from
// iverilog to the TT flow's Yosys, sees the same mask ROM with no
// parameter plumbing. The HEX parameter remains as a test override
// ($readmemh) for fixture images. With no write port the array
// synthesizes to pure combinational constants - inherently SEU-immune,
// which is why the firmware lives here and not in RAM.
//
// Two independent read ports, both combinational single-cycle:
//   * ibus: SERV instruction fetches, wired point to point (not through
//     the bus - instruction fetch must not compete with data traffic on a
//     single-master interconnect, and constants have no port conflicts)
//   * dbus: a bus slave like every other block, so firmware can read its
//     own image (checksum self-test at boot)
//
// ZIRH-2 memory map (bus slot = adr[14:12]):
//   slot 0  0x0000_0000  this ROM (1 KB)
//   slot 1  0x0000_1000  zirh_ecc_ram (64 B), stack top at 0x1040
//   slot 2  0x0000_2000  zirh_uart_regs
// =============================================================================

`default_nettype none

module zirh_rom #(
    parameter HEX = ""    // test override; empty = the committed rom_init.vh
) (
    input  wire        clk,   // SYNTH (FPGA twin) registered reads only
    // instruction port (SERV ibus, point to point)
    input  wire [31:0] i_adr_i,
    output wire [31:0] i_rdt_o,

    // data port (bus slave)
    input  wire        cyc_i,
    input  wire [31:0] adr_i,
    output wire [31:0] rdt_o,
    output wire        ack_o
);

    reg [31:0] mem [0:255];

    generate
        if (HEX != "") begin : g_load
            initial $readmemh(HEX, mem);
        end else begin : g_fw
            initial begin
                `include "rom_init.vh"
            end
        end
    endgenerate

`ifdef SYNTH
    // FPGA twin: register both read ports so yosys maps the 256x32 array
    // to block RAM instead of ~8 Kbit of LUTs - the fit lever the full
    // (5-interface) design needs on UP5K. Timing-safe by construction:
    // the SoC's ibus_ack is already one cycle delayed (ibus_cyc &
    // ~ibus_ack), so a registered fetch delivers exactly on the ack
    // cycle SERV samples; the dbus side reads through the SoC's own
    // registered dbus_rdt_q. A twin/silicon delta, ASIC keeps the
    // combinational constants (inherently SEU-immune, the whole reason
    // firmware lives in ROM).
    reg [31:0] i_rdt_r, rdt_r;
    always @(posedge clk) begin
        i_rdt_r <= mem[i_adr_i[9:2]];
        rdt_r   <= mem[adr_i[9:2]];
    end
    assign i_rdt_o = i_rdt_r;
    assign rdt_o   = rdt_r;
    assign ack_o   = cyc_i;
`else
    assign i_rdt_o = mem[i_adr_i[9:2]];
    assign rdt_o   = mem[adr_i[9:2]];
    assign ack_o   = cyc_i;
`endif

endmodule

`default_nettype wire
