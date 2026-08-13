// ZIRH - arch-test harness: the integrated SERV against rv32i (H46)
`timescale 1ns / 1ps

module tb_arch;
    reg clk = 0;
    reg rst = 1;
    always #20 clk = ~clk;

    // 2 MB flat RAM at 0x0 (the jal test's jump matrix is a 1.75 MB
    // image); SERV never overlaps ibus and dbus cycles
    reg [31:0] mem [0:524287];

    wire [31:0] ibus_adr, dbus_adr, dbus_dat;
    wire [3:0]  dbus_sel;
    wire        ibus_cyc, dbus_cyc, dbus_we;
    reg  [31:0] ibus_rdt, dbus_rdt;
    reg         ibus_ack, dbus_ack;

    serv_rf_top #(
        .RESET_PC (32'h0000_0000),
        .WITH_CSR (1)
    ) u_cpu (
        .clk(clk), .i_rst(rst), .i_timer_irq(1'b0),
        .o_ibus_adr(ibus_adr), .o_ibus_cyc(ibus_cyc),
        .i_ibus_rdt(ibus_rdt), .i_ibus_ack(ibus_ack),
        .o_dbus_adr(dbus_adr), .o_dbus_dat(dbus_dat),
        .o_dbus_sel(dbus_sel), .o_dbus_we(dbus_we),
        .o_dbus_cyc(dbus_cyc), .i_dbus_rdt(dbus_rdt),
        .i_dbus_ack(dbus_ack),
        .o_ext_rs1(), .o_ext_rs2(), .o_ext_funct3(),
        .i_ext_rd(32'b0), .i_ext_ready(1'b0), .o_mdu_valid());

    // registered acks, single-cycle memory
    reg [31:0] sigb, sige;
    integer f, a;
    reg [1023:0] hexfile, sigfile;

    always @(posedge clk) begin
        ibus_ack <= ibus_cyc & ~ibus_ack;
        ibus_rdt <= mem[ibus_adr[20:2]];
        dbus_ack <= dbus_cyc & ~dbus_ack;
        dbus_rdt <= mem[dbus_adr[20:2]];
        if (dbus_cyc & dbus_we & ~dbus_ack) begin
            if (dbus_adr[31:21] == 0) begin
                if (dbus_sel[0]) mem[dbus_adr[20:2]][7:0]   <= dbus_dat[7:0];
                if (dbus_sel[1]) mem[dbus_adr[20:2]][15:8]  <= dbus_dat[15:8];
                if (dbus_sel[2]) mem[dbus_adr[20:2]][23:16] <= dbus_dat[23:16];
                if (dbus_sel[3]) mem[dbus_adr[20:2]][31:24] <= dbus_dat[31:24];
            end else if (dbus_adr == 32'h0020_0000) sigb <= dbus_dat;
            else if (dbus_adr == 32'h0020_0004) sige <= dbus_dat;
            else if (dbus_adr == 32'h0020_0008) begin
                f = $fopen(sigfile, "w");
                for (a = sigb; a < sige; a = a + 4)
                    $fdisplay(f, "%08x", mem[a[20:2]]);
                $fclose(f);
                $display("ARCH DONE sig %08x..%08x", sigb, sige);
                $finish;
            end
        end
    end

    integer cyc = 0;
    always @(posedge clk) begin
        cyc = cyc + 1;
        if (cyc > 240_000_000) begin
            $display("ARCH TIMEOUT");
            $fatal(1);
        end
    end

    initial begin
        if (!$value$plusargs("HEX=%s", hexfile)) $fatal(1, "no HEX");
        if (!$value$plusargs("SIG=%s", sigfile)) $fatal(1, "no SIG");
        $readmemh(hexfile, mem);
        repeat (8) @(posedge clk);
        rst = 0;
    end
endmodule
