set sigs [list f_ring.clk {f_ring.flip_a[7:0]} {f_ring.flip_b[7:0]} {f_ring.shadow[7:0]} {f_ring.u_ff_a.q_o[7:0]} {f_ring.u_ff_b.q_o[7:0]} {f_ring.u_ff_c.q_o[7:0]}]
gtkwave::addSignalsFromList $sigs
gtkwave::/Edit/Data_Format/Hex
gtkwave::highlightSignalsFromList {f_ring.u_ff_a.q_o[7:0]}
gtkwave::/Edit/Alias_Highlighted_Trace replica_a_q
gtkwave::unhighlightSignalsFromList {f_ring.u_ff_a.q_o[7:0]}
gtkwave::highlightSignalsFromList {f_ring.u_ff_b.q_o[7:0]}
gtkwave::/Edit/Alias_Highlighted_Trace replica_b_q
gtkwave::unhighlightSignalsFromList {f_ring.u_ff_b.q_o[7:0]}
gtkwave::highlightSignalsFromList {f_ring.u_ff_c.q_o[7:0]}
gtkwave::/Edit/Alias_Highlighted_Trace replica_c_q
gtkwave::unhighlightSignalsFromList {f_ring.u_ff_c.q_o[7:0]}
gtkwave::highlightSignalsFromList {f_ring.shadow[7:0]}
gtkwave::/Edit/Alias_Highlighted_Trace golden_ring
gtkwave::unhighlightSignalsFromList {f_ring.shadow[7:0]}
gtkwave::/Time/Zoom/Zoom_Full
gtkwave::/File/Grab_To_File formal/out/escape_n8.png
gtkwave::/File/Quit
