// tmr-guard demo: a voted register pair whose hardening the optimizer
// WILL delete the moment the attribute is gone. Run the tool both
// ways and watch it catch the collapse - that is the whole product.
`default_nettype none

(* keep_hierarchy *) module demo_rep #(
    parameter WIDTH = 8
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire [WIDTH-1:0] d_i,
    output reg  [WIDTH-1:0] q_o
);
    always @(posedge clk)
        if (!rst_n) q_o <= {WIDTH{1'b0}};
        else        q_o <= d_i;
endmodule

module demo_top (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] d_i,
    input  wire       en_i,
    output wire [7:0] q_o,
    output wire       err_o
);
    wire [7:0] qa, qb, qc;
    wire [7:0] voted = (qa & qb) | (qb & qc) | (qa & qc);
    wire [7:0] d = en_i ? d_i : voted;

    demo_rep u_a (.clk(clk), .rst_n(rst_n), .d_i(d), .q_o(qa));
    demo_rep u_b (.clk(clk), .rst_n(rst_n), .d_i(d), .q_o(qb));
    demo_rep u_c (.clk(clk), .rst_n(rst_n), .d_i(d), .q_o(qc));

    assign q_o  = voted;
    assign err_o = |((qa ^ qb) | (qb ^ qc) | (qa ^ qc));
endmodule

`default_nettype wire
