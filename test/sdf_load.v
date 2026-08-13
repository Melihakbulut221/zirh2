// ZIRH - SDF annotation shim (G30): +SDF=<file> applies corner delays
// to the netlist under tb.user_project before time zero.
module sdf_load;
    reg [1023:0] f;
    initial begin
        if ($value$plusargs("SDF=%s", f)) begin
            $sdf_annotate(f, tb.user_project);
            $display("SDF annotated: %0s", f);
        end
    end
endmodule
