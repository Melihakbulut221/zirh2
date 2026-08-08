module zirh_tmr_ff32 (clk,
    rst_n,
    d_i,
    q_o);
 input clk;
 input rst_n;
 input [31:0] d_i;
 output [31:0] q_o;

 wire net1;
 wire net2;
 wire net3;
 wire net4;
 wire net5;
 wire net6;
 wire net7;
 wire net8;
 wire net9;
 wire net10;
 wire net11;
 wire net12;
 wire net13;
 wire net14;
 wire net15;
 wire net16;
 wire net17;
 wire net18;
 wire net19;
 wire net20;
 wire net21;
 wire net22;
 wire net23;
 wire net24;
 wire net25;
 wire net26;
 wire net27;
 wire net28;
 wire net29;
 wire net30;
 wire net31;
 wire net32;
 wire net34;
 wire net35;
 wire net36;
 wire net37;
 wire net38;
 wire net39;
 wire net40;
 wire net41;
 wire net42;
 wire net43;
 wire net44;
 wire net45;
 wire net46;
 wire net47;
 wire net48;
 wire net49;
 wire net50;
 wire net51;
 wire net52;
 wire net53;
 wire net54;
 wire net55;
 wire net56;
 wire net57;
 wire net58;
 wire net59;
 wire net60;
 wire net61;
 wire net62;
 wire net63;
 wire net64;
 wire net65;
 wire net33;
 wire \u_core/_000_ ;
 wire \u_core/_001_ ;
 wire \u_core/_002_ ;
 wire \u_core/_003_ ;
 wire \u_core/_004_ ;
 wire \u_core/_005_ ;
 wire \u_core/_006_ ;
 wire \u_core/_007_ ;
 wire \u_core/_008_ ;
 wire \u_core/_009_ ;
 wire \u_core/_010_ ;
 wire \u_core/_011_ ;
 wire \u_core/_012_ ;
 wire \u_core/_013_ ;
 wire \u_core/_014_ ;
 wire \u_core/_015_ ;
 wire \u_core/_016_ ;
 wire \u_core/_017_ ;
 wire \u_core/_018_ ;
 wire \u_core/_019_ ;
 wire \u_core/_020_ ;
 wire \u_core/_021_ ;
 wire \u_core/_022_ ;
 wire \u_core/_023_ ;
 wire \u_core/_024_ ;
 wire \u_core/_025_ ;
 wire \u_core/_026_ ;
 wire \u_core/_027_ ;
 wire \u_core/_028_ ;
 wire \u_core/_029_ ;
 wire \u_core/_030_ ;
 wire \u_core/_031_ ;
 wire net71;
 wire net72;
 wire net73;
 wire net74;
 wire net75;
 wire net76;
 wire net77;
 wire net78;
 wire net79;
 wire net80;
 wire net81;
 wire net82;
 wire net83;
 wire net84;
 wire net85;
 wire net86;
 wire net87;
 wire net88;
 wire net89;
 wire net90;
 wire net91;
 wire net92;
 wire net93;
 wire net94;
 wire net95;
 wire net96;
 wire net97;
 wire net98;
 wire net99;
 wire net100;
 wire net101;
 wire clknet_0_clk;
 wire \u_core/net66 ;
 wire \u_core/net67 ;
 wire \u_core/net68 ;
 wire \u_core/net69 ;
 wire \u_core/net70 ;
 wire net;
 wire clknet_3_0__leaf_clk;
 wire clknet_3_1__leaf_clk;
 wire clknet_3_2__leaf_clk;
 wire clknet_3_3__leaf_clk;
 wire clknet_3_4__leaf_clk;
 wire clknet_3_5__leaf_clk;
 wire clknet_3_6__leaf_clk;
 wire clknet_3_7__leaf_clk;

 sg13g2_decap_8 FILLER_0_0 ();
 sg13g2_decap_8 FILLER_0_131 ();
 sg13g2_decap_8 FILLER_0_138 ();
 sg13g2_fill_2 FILLER_0_14 ();
 sg13g2_fill_1 FILLER_0_145 ();
 sg13g2_fill_1 FILLER_0_16 ();
 sg13g2_decap_8 FILLER_0_7 ();
 sg13g2_fill_2 FILLER_0_72 ();
 sg13g2_fill_1 FILLER_0_74 ();
 sg13g2_fill_2 FILLER_0_95 ();
 sg13g2_decap_8 FILLER_10_104 ();
 sg13g2_decap_4 FILLER_10_111 ();
 sg13g2_fill_2 FILLER_10_147 ();
 sg13g2_fill_1 FILLER_10_149 ();
 sg13g2_decap_8 FILLER_10_37 ();
 sg13g2_fill_1 FILLER_10_4 ();
 sg13g2_decap_8 FILLER_10_44 ();
 sg13g2_decap_8 FILLER_10_51 ();
 sg13g2_decap_8 FILLER_10_58 ();
 sg13g2_decap_8 FILLER_10_65 ();
 sg13g2_decap_8 FILLER_10_72 ();
 sg13g2_decap_8 FILLER_11_102 ();
 sg13g2_decap_4 FILLER_11_109 ();
 sg13g2_decap_8 FILLER_11_37 ();
 sg13g2_fill_2 FILLER_11_44 ();
 sg13g2_fill_1 FILLER_11_46 ();
 sg13g2_decap_8 FILLER_11_74 ();
 sg13g2_decap_8 FILLER_11_81 ();
 sg13g2_decap_8 FILLER_11_88 ();
 sg13g2_decap_8 FILLER_11_95 ();
 sg13g2_decap_8 FILLER_12_102 ();
 sg13g2_decap_8 FILLER_12_109 ();
 sg13g2_fill_2 FILLER_12_116 ();
 sg13g2_fill_1 FILLER_12_118 ();
 sg13g2_decap_8 FILLER_12_23 ();
 sg13g2_fill_1 FILLER_12_30 ();
 sg13g2_decap_8 FILLER_12_60 ();
 sg13g2_decap_8 FILLER_12_67 ();
 sg13g2_decap_8 FILLER_12_74 ();
 sg13g2_fill_2 FILLER_12_8 ();
 sg13g2_decap_8 FILLER_12_81 ();
 sg13g2_decap_8 FILLER_12_88 ();
 sg13g2_decap_8 FILLER_12_95 ();
 sg13g2_decap_8 FILLER_13_103 ();
 sg13g2_decap_4 FILLER_13_110 ();
 sg13g2_fill_2 FILLER_13_114 ();
 sg13g2_decap_8 FILLER_13_36 ();
 sg13g2_decap_8 FILLER_13_43 ();
 sg13g2_decap_8 FILLER_13_50 ();
 sg13g2_decap_8 FILLER_13_57 ();
 sg13g2_decap_8 FILLER_13_64 ();
 sg13g2_decap_8 FILLER_13_71 ();
 sg13g2_decap_8 FILLER_13_78 ();
 sg13g2_fill_1 FILLER_13_8 ();
 sg13g2_decap_8 FILLER_13_85 ();
 sg13g2_decap_8 FILLER_13_96 ();
 sg13g2_decap_8 FILLER_14_0 ();
 sg13g2_decap_8 FILLER_14_114 ();
 sg13g2_fill_2 FILLER_14_121 ();
 sg13g2_decap_8 FILLER_14_18 ();
 sg13g2_decap_8 FILLER_14_25 ();
 sg13g2_decap_8 FILLER_14_32 ();
 sg13g2_decap_8 FILLER_14_39 ();
 sg13g2_decap_8 FILLER_14_46 ();
 sg13g2_decap_8 FILLER_14_53 ();
 sg13g2_decap_8 FILLER_14_60 ();
 sg13g2_decap_8 FILLER_14_67 ();
 sg13g2_decap_8 FILLER_14_7 ();
 sg13g2_decap_8 FILLER_14_74 ();
 sg13g2_decap_4 FILLER_14_81 ();
 sg13g2_fill_2 FILLER_14_85 ();
 sg13g2_decap_8 FILLER_15_102 ();
 sg13g2_decap_8 FILLER_15_109 ();
 sg13g2_decap_8 FILLER_15_11 ();
 sg13g2_decap_8 FILLER_15_116 ();
 sg13g2_decap_4 FILLER_15_123 ();
 sg13g2_fill_2 FILLER_15_127 ();
 sg13g2_fill_1 FILLER_15_133 ();
 sg13g2_decap_8 FILLER_15_18 ();
 sg13g2_decap_8 FILLER_15_25 ();
 sg13g2_decap_8 FILLER_15_32 ();
 sg13g2_decap_8 FILLER_15_39 ();
 sg13g2_decap_8 FILLER_15_4 ();
 sg13g2_decap_8 FILLER_15_46 ();
 sg13g2_decap_8 FILLER_15_53 ();
 sg13g2_decap_8 FILLER_15_60 ();
 sg13g2_decap_8 FILLER_15_67 ();
 sg13g2_fill_2 FILLER_15_74 ();
 sg13g2_decap_8 FILLER_15_81 ();
 sg13g2_decap_8 FILLER_15_88 ();
 sg13g2_decap_8 FILLER_15_95 ();
 sg13g2_decap_8 FILLER_16_100 ();
 sg13g2_fill_2 FILLER_16_107 ();
 sg13g2_decap_8 FILLER_16_114 ();
 sg13g2_fill_1 FILLER_16_121 ();
 sg13g2_fill_1 FILLER_16_149 ();
 sg13g2_fill_2 FILLER_16_19 ();
 sg13g2_fill_1 FILLER_16_4 ();
 sg13g2_decap_4 FILLER_16_48 ();
 sg13g2_fill_2 FILLER_16_52 ();
 sg13g2_decap_4 FILLER_16_85 ();
 sg13g2_decap_8 FILLER_16_93 ();
 sg13g2_fill_1 FILLER_17_11 ();
 sg13g2_fill_1 FILLER_17_116 ();
 sg13g2_fill_2 FILLER_17_144 ();
 sg13g2_decap_8 FILLER_17_4 ();
 sg13g2_decap_8 FILLER_18_0 ();
 sg13g2_fill_2 FILLER_18_111 ();
 sg13g2_decap_8 FILLER_18_14 ();
 sg13g2_fill_2 FILLER_18_21 ();
 sg13g2_fill_1 FILLER_18_23 ();
 sg13g2_decap_8 FILLER_18_7 ();
 sg13g2_fill_1 FILLER_18_86 ();
 sg13g2_decap_8 FILLER_1_0 ();
 sg13g2_decap_4 FILLER_1_124 ();
 sg13g2_fill_1 FILLER_1_128 ();
 sg13g2_decap_4 FILLER_1_133 ();
 sg13g2_fill_1 FILLER_1_137 ();
 sg13g2_decap_4 FILLER_1_14 ();
 sg13g2_fill_1 FILLER_1_18 ();
 sg13g2_decap_8 FILLER_1_7 ();
 sg13g2_fill_1 FILLER_1_92 ();
 sg13g2_decap_8 FILLER_2_0 ();
 sg13g2_decap_8 FILLER_2_113 ();
 sg13g2_fill_2 FILLER_2_120 ();
 sg13g2_fill_1 FILLER_2_122 ();
 sg13g2_decap_4 FILLER_2_46 ();
 sg13g2_fill_1 FILLER_2_50 ();
 sg13g2_fill_2 FILLER_2_7 ();
 sg13g2_fill_1 FILLER_2_9 ();
 sg13g2_decap_8 FILLER_3_0 ();
 sg13g2_decap_8 FILLER_3_103 ();
 sg13g2_decap_8 FILLER_3_110 ();
 sg13g2_fill_1 FILLER_3_117 ();
 sg13g2_decap_8 FILLER_3_42 ();
 sg13g2_decap_8 FILLER_3_49 ();
 sg13g2_decap_4 FILLER_3_56 ();
 sg13g2_fill_2 FILLER_3_64 ();
 sg13g2_fill_1 FILLER_3_66 ();
 sg13g2_fill_2 FILLER_3_7 ();
 sg13g2_decap_8 FILLER_3_71 ();
 sg13g2_decap_8 FILLER_3_78 ();
 sg13g2_fill_2 FILLER_3_85 ();
 sg13g2_fill_1 FILLER_3_9 ();
 sg13g2_decap_8 FILLER_3_91 ();
 sg13g2_fill_1 FILLER_3_98 ();
 sg13g2_decap_8 FILLER_4_101 ();
 sg13g2_decap_8 FILLER_4_108 ();
 sg13g2_fill_2 FILLER_4_115 ();
 sg13g2_decap_4 FILLER_4_15 ();
 sg13g2_fill_1 FILLER_4_19 ();
 sg13g2_decap_8 FILLER_4_24 ();
 sg13g2_decap_8 FILLER_4_31 ();
 sg13g2_decap_8 FILLER_4_38 ();
 sg13g2_fill_2 FILLER_4_45 ();
 sg13g2_fill_1 FILLER_4_47 ();
 sg13g2_decap_8 FILLER_4_52 ();
 sg13g2_decap_8 FILLER_4_59 ();
 sg13g2_decap_8 FILLER_4_66 ();
 sg13g2_decap_8 FILLER_4_73 ();
 sg13g2_decap_8 FILLER_4_8 ();
 sg13g2_decap_8 FILLER_4_80 ();
 sg13g2_decap_8 FILLER_4_87 ();
 sg13g2_decap_8 FILLER_4_94 ();
 sg13g2_decap_8 FILLER_5_105 ();
 sg13g2_decap_8 FILLER_5_112 ();
 sg13g2_decap_8 FILLER_5_15 ();
 sg13g2_decap_8 FILLER_5_22 ();
 sg13g2_decap_8 FILLER_5_29 ();
 sg13g2_decap_8 FILLER_5_36 ();
 sg13g2_decap_8 FILLER_5_70 ();
 sg13g2_decap_8 FILLER_5_77 ();
 sg13g2_fill_2 FILLER_5_8 ();
 sg13g2_decap_8 FILLER_5_84 ();
 sg13g2_decap_8 FILLER_5_91 ();
 sg13g2_decap_8 FILLER_5_98 ();
 sg13g2_decap_8 FILLER_6_105 ();
 sg13g2_fill_1 FILLER_6_112 ();
 sg13g2_decap_8 FILLER_6_35 ();
 sg13g2_decap_8 FILLER_6_42 ();
 sg13g2_decap_8 FILLER_6_49 ();
 sg13g2_decap_8 FILLER_6_56 ();
 sg13g2_decap_8 FILLER_6_63 ();
 sg13g2_decap_8 FILLER_6_70 ();
 sg13g2_decap_8 FILLER_6_77 ();
 sg13g2_decap_8 FILLER_6_84 ();
 sg13g2_decap_8 FILLER_6_91 ();
 sg13g2_decap_8 FILLER_6_98 ();
 sg13g2_decap_8 FILLER_7_104 ();
 sg13g2_fill_2 FILLER_7_147 ();
 sg13g2_fill_1 FILLER_7_149 ();
 sg13g2_decap_8 FILLER_7_41 ();
 sg13g2_fill_1 FILLER_7_48 ();
 sg13g2_decap_8 FILLER_7_76 ();
 sg13g2_decap_8 FILLER_7_83 ();
 sg13g2_decap_8 FILLER_7_90 ();
 sg13g2_decap_8 FILLER_7_97 ();
 sg13g2_decap_8 FILLER_8_100 ();
 sg13g2_decap_8 FILLER_8_107 ();
 sg13g2_decap_8 FILLER_8_114 ();
 sg13g2_fill_1 FILLER_8_137 ();
 sg13g2_decap_8 FILLER_8_23 ();
 sg13g2_decap_8 FILLER_8_30 ();
 sg13g2_decap_8 FILLER_8_37 ();
 sg13g2_fill_2 FILLER_8_4 ();
 sg13g2_decap_8 FILLER_8_44 ();
 sg13g2_fill_2 FILLER_8_51 ();
 sg13g2_fill_1 FILLER_8_53 ();
 sg13g2_decap_8 FILLER_8_58 ();
 sg13g2_decap_8 FILLER_8_65 ();
 sg13g2_decap_8 FILLER_8_72 ();
 sg13g2_decap_8 FILLER_8_79 ();
 sg13g2_decap_8 FILLER_8_86 ();
 sg13g2_decap_8 FILLER_8_93 ();
 sg13g2_decap_8 FILLER_9_106 ();
 sg13g2_decap_8 FILLER_9_113 ();
 sg13g2_decap_8 FILLER_9_12 ();
 sg13g2_decap_4 FILLER_9_120 ();
 sg13g2_fill_1 FILLER_9_124 ();
 sg13g2_fill_1 FILLER_9_129 ();
 sg13g2_decap_8 FILLER_9_19 ();
 sg13g2_decap_8 FILLER_9_26 ();
 sg13g2_decap_4 FILLER_9_33 ();
 sg13g2_fill_2 FILLER_9_37 ();
 sg13g2_decap_8 FILLER_9_64 ();
 sg13g2_decap_8 FILLER_9_71 ();
 sg13g2_decap_8 FILLER_9_78 ();
 sg13g2_decap_8 FILLER_9_85 ();
 sg13g2_decap_8 FILLER_9_92 ();
 sg13g2_decap_8 FILLER_9_99 ();
 sg13g2_buf_16 clkbuf_0_clk (.X(clknet_0_clk),
    .A(clk));
 sg13g2_buf_16 clkbuf_3_0__f_clk (.X(clknet_3_0__leaf_clk),
    .A(clknet_0_clk));
 sg13g2_buf_16 clkbuf_3_1__f_clk (.X(clknet_3_1__leaf_clk),
    .A(clknet_0_clk));
 sg13g2_buf_16 clkbuf_3_2__f_clk (.X(clknet_3_2__leaf_clk),
    .A(clknet_0_clk));
 sg13g2_buf_16 clkbuf_3_3__f_clk (.X(clknet_3_3__leaf_clk),
    .A(clknet_0_clk));
 sg13g2_buf_16 clkbuf_3_4__f_clk (.X(clknet_3_4__leaf_clk),
    .A(clknet_0_clk));
 sg13g2_buf_16 clkbuf_3_5__f_clk (.X(clknet_3_5__leaf_clk),
    .A(clknet_0_clk));
 sg13g2_buf_16 clkbuf_3_6__f_clk (.X(clknet_3_6__leaf_clk),
    .A(clknet_0_clk));
 sg13g2_buf_16 clkbuf_3_7__f_clk (.X(clknet_3_7__leaf_clk),
    .A(clknet_0_clk));
 sg13g2_buf_1 input1 (.A(d_i[0]),
    .X(net1));
 sg13g2_buf_1 input10 (.A(d_i[18]),
    .X(net10));
 sg13g2_buf_1 input11 (.A(d_i[19]),
    .X(net11));
 sg13g2_buf_1 input12 (.A(d_i[1]),
    .X(net12));
 sg13g2_buf_1 input13 (.A(d_i[20]),
    .X(net13));
 sg13g2_buf_1 input14 (.A(d_i[21]),
    .X(net14));
 sg13g2_buf_1 input15 (.A(d_i[22]),
    .X(net15));
 sg13g2_buf_1 input16 (.A(d_i[23]),
    .X(net16));
 sg13g2_buf_1 input17 (.A(d_i[24]),
    .X(net17));
 sg13g2_buf_1 input18 (.A(d_i[25]),
    .X(net18));
 sg13g2_buf_1 input19 (.A(d_i[26]),
    .X(net19));
 sg13g2_buf_1 input2 (.A(d_i[10]),
    .X(net2));
 sg13g2_buf_1 input20 (.A(d_i[27]),
    .X(net20));
 sg13g2_buf_1 input21 (.A(d_i[28]),
    .X(net21));
 sg13g2_buf_1 input22 (.A(d_i[29]),
    .X(net22));
 sg13g2_buf_1 input23 (.A(d_i[2]),
    .X(net23));
 sg13g2_buf_1 input24 (.A(d_i[30]),
    .X(net24));
 sg13g2_buf_1 input25 (.A(d_i[31]),
    .X(net25));
 sg13g2_buf_1 input26 (.A(d_i[3]),
    .X(net26));
 sg13g2_buf_1 input27 (.A(d_i[4]),
    .X(net27));
 sg13g2_buf_1 input28 (.A(d_i[5]),
    .X(net28));
 sg13g2_buf_1 input29 (.A(d_i[6]),
    .X(net29));
 sg13g2_buf_1 input3 (.A(d_i[11]),
    .X(net3));
 sg13g2_buf_1 input30 (.A(d_i[7]),
    .X(net30));
 sg13g2_buf_1 input31 (.A(d_i[8]),
    .X(net31));
 sg13g2_buf_1 input32 (.A(d_i[9]),
    .X(net32));
 sg13g2_buf_1 input33 (.A(rst_n),
    .X(net33));
 sg13g2_buf_1 input4 (.A(d_i[12]),
    .X(net4));
 sg13g2_buf_1 input5 (.A(d_i[13]),
    .X(net5));
 sg13g2_buf_1 input6 (.A(d_i[14]),
    .X(net6));
 sg13g2_buf_1 input7 (.A(d_i[15]),
    .X(net7));
 sg13g2_buf_1 input8 (.A(d_i[16]),
    .X(net8));
 sg13g2_buf_1 input9 (.A(d_i[17]),
    .X(net9));
 sg13g2_buf_1 output34 (.A(net34),
    .X(q_o[0]));
 sg13g2_buf_1 output35 (.A(net35),
    .X(q_o[10]));
 sg13g2_buf_1 output36 (.A(net36),
    .X(q_o[11]));
 sg13g2_buf_1 output37 (.A(net37),
    .X(q_o[12]));
 sg13g2_buf_1 output38 (.A(net38),
    .X(q_o[13]));
 sg13g2_buf_1 output39 (.A(net39),
    .X(q_o[14]));
 sg13g2_buf_1 output40 (.A(net40),
    .X(q_o[15]));
 sg13g2_buf_1 output41 (.A(net41),
    .X(q_o[16]));
 sg13g2_buf_1 output42 (.A(net42),
    .X(q_o[17]));
 sg13g2_buf_1 output43 (.A(net43),
    .X(q_o[18]));
 sg13g2_buf_1 output44 (.A(net44),
    .X(q_o[19]));
 sg13g2_buf_1 output45 (.A(net45),
    .X(q_o[1]));
 sg13g2_buf_1 output46 (.A(net46),
    .X(q_o[20]));
 sg13g2_buf_1 output47 (.A(net47),
    .X(q_o[21]));
 sg13g2_buf_1 output48 (.A(net48),
    .X(q_o[22]));
 sg13g2_buf_1 output49 (.A(net49),
    .X(q_o[23]));
 sg13g2_buf_1 output50 (.A(net50),
    .X(q_o[24]));
 sg13g2_buf_1 output51 (.A(net51),
    .X(q_o[25]));
 sg13g2_buf_1 output52 (.A(net52),
    .X(q_o[26]));
 sg13g2_buf_1 output53 (.A(net53),
    .X(q_o[27]));
 sg13g2_buf_1 output54 (.A(net54),
    .X(q_o[28]));
 sg13g2_buf_1 output55 (.A(net55),
    .X(q_o[29]));
 sg13g2_buf_1 output56 (.A(net56),
    .X(q_o[2]));
 sg13g2_buf_1 output57 (.A(net57),
    .X(q_o[30]));
 sg13g2_buf_1 output58 (.A(net58),
    .X(q_o[31]));
 sg13g2_buf_1 output59 (.A(net59),
    .X(q_o[3]));
 sg13g2_buf_1 output60 (.A(net60),
    .X(q_o[4]));
 sg13g2_buf_1 output61 (.A(net61),
    .X(q_o[5]));
 sg13g2_buf_1 output62 (.A(net62),
    .X(q_o[6]));
 sg13g2_buf_1 output63 (.A(net63),
    .X(q_o[7]));
 sg13g2_buf_1 output64 (.A(net64),
    .X(q_o[8]));
 sg13g2_buf_1 output65 (.A(net65),
    .X(q_o[9]));
 sg13g2_and2_1 \u_core/_064_  (.A(net9),
    .B(\u_core/net68 ),
    .X(\u_core/_000_ ));
 sg13g2_and2_1 \u_core/_065_  (.A(\u_core/net68 ),
    .B(net10),
    .X(\u_core/_001_ ));
 sg13g2_and2_1 \u_core/_066_  (.A(\u_core/net66 ),
    .B(net11),
    .X(\u_core/_002_ ));
 sg13g2_and2_1 \u_core/_067_  (.A(\u_core/net67 ),
    .B(net13),
    .X(\u_core/_003_ ));
 sg13g2_and2_1 \u_core/_068_  (.A(\u_core/net67 ),
    .B(net14),
    .X(\u_core/_004_ ));
 sg13g2_and2_1 \u_core/_069_  (.A(\u_core/net69 ),
    .B(net15),
    .X(\u_core/_005_ ));
 sg13g2_and2_1 \u_core/_070_  (.A(\u_core/net69 ),
    .B(net16),
    .X(\u_core/_006_ ));
 sg13g2_and2_1 \u_core/_071_  (.A(\u_core/net68 ),
    .B(net17),
    .X(\u_core/_007_ ));
 sg13g2_and2_1 \u_core/_072_  (.A(\u_core/net66 ),
    .B(net18),
    .X(\u_core/_008_ ));
 sg13g2_and2_1 \u_core/_073_  (.A(\u_core/net69 ),
    .B(net19),
    .X(\u_core/_009_ ));
 sg13g2_and2_1 \u_core/_074_  (.A(\u_core/net66 ),
    .B(net20),
    .X(\u_core/_010_ ));
 sg13g2_and2_1 \u_core/_075_  (.A(\u_core/net68 ),
    .B(net21),
    .X(\u_core/_011_ ));
 sg13g2_and2_1 \u_core/_076_  (.A(\u_core/net68 ),
    .B(net22),
    .X(\u_core/_012_ ));
 sg13g2_and2_1 \u_core/_077_  (.A(\u_core/net67 ),
    .B(net24),
    .X(\u_core/_013_ ));
 sg13g2_and2_1 \u_core/_078_  (.A(\u_core/net67 ),
    .B(net25),
    .X(\u_core/_014_ ));
 sg13g2_and2_1 \u_core/_079_  (.A(\u_core/net66 ),
    .B(net1),
    .X(\u_core/_015_ ));
 sg13g2_and2_1 \u_core/_080_  (.A(\u_core/net68 ),
    .B(net12),
    .X(\u_core/_016_ ));
 sg13g2_and2_1 \u_core/_081_  (.A(\u_core/net67 ),
    .B(net23),
    .X(\u_core/_017_ ));
 sg13g2_and2_1 \u_core/_082_  (.A(\u_core/net68 ),
    .B(net26),
    .X(\u_core/_018_ ));
 sg13g2_and2_1 \u_core/_083_  (.A(\u_core/net67 ),
    .B(net27),
    .X(\u_core/_019_ ));
 sg13g2_and2_1 \u_core/_084_  (.A(\u_core/net69 ),
    .B(net28),
    .X(\u_core/_020_ ));
 sg13g2_and2_1 \u_core/_085_  (.A(\u_core/net66 ),
    .B(net29),
    .X(\u_core/_021_ ));
 sg13g2_and2_1 \u_core/_086_  (.A(\u_core/net69 ),
    .B(net30),
    .X(\u_core/_022_ ));
 sg13g2_and2_1 \u_core/_087_  (.A(\u_core/net66 ),
    .B(net31),
    .X(\u_core/_023_ ));
 sg13g2_and2_1 \u_core/_088_  (.A(\u_core/net68 ),
    .B(net32),
    .X(\u_core/_024_ ));
 sg13g2_and2_1 \u_core/_089_  (.A(\u_core/net69 ),
    .B(net2),
    .X(\u_core/_025_ ));
 sg13g2_and2_1 \u_core/_090_  (.A(\u_core/net66 ),
    .B(net3),
    .X(\u_core/_026_ ));
 sg13g2_and2_1 \u_core/_091_  (.A(\u_core/net69 ),
    .B(net4),
    .X(\u_core/_027_ ));
 sg13g2_and2_1 \u_core/_092_  (.A(\u_core/net70 ),
    .B(net5),
    .X(\u_core/_028_ ));
 sg13g2_and2_1 \u_core/_093_  (.A(\u_core/net69 ),
    .B(net6),
    .X(\u_core/_029_ ));
 sg13g2_and2_1 \u_core/_094_  (.A(\u_core/net67 ),
    .B(net7),
    .X(\u_core/_030_ ));
 sg13g2_and2_1 \u_core/_095_  (.A(\u_core/net66 ),
    .B(net8),
    .X(\u_core/_031_ ));
 sg13g2_dfrbpq_1 \u_core/_096_  (.RESET_B(net),
    .D(\u_core/_000_ ),
    .Q(net42),
    .CLK(clknet_3_4__leaf_clk));
 sg13g2_tiehi \u_core/_096__71  (.L_HI(net));
 sg13g2_dfrbpq_1 \u_core/_097_  (.RESET_B(net101),
    .D(\u_core/_001_ ),
    .Q(net43),
    .CLK(clknet_3_4__leaf_clk));
 sg13g2_tiehi \u_core/_097__102  (.L_HI(net101));
 sg13g2_dfrbpq_1 \u_core/_098_  (.RESET_B(net100),
    .D(\u_core/_002_ ),
    .Q(net44),
    .CLK(clknet_3_2__leaf_clk));
 sg13g2_tiehi \u_core/_098__101  (.L_HI(net100));
 sg13g2_dfrbpq_1 \u_core/_099_  (.RESET_B(net99),
    .D(\u_core/_003_ ),
    .Q(net46),
    .CLK(clknet_3_3__leaf_clk));
 sg13g2_tiehi \u_core/_099__100  (.L_HI(net99));
 sg13g2_dfrbpq_1 \u_core/_100_  (.RESET_B(net98),
    .D(\u_core/_004_ ),
    .Q(net47),
    .CLK(clknet_3_3__leaf_clk));
 sg13g2_tiehi \u_core/_100__99  (.L_HI(net98));
 sg13g2_dfrbpq_1 \u_core/_101_  (.RESET_B(net97),
    .D(\u_core/_005_ ),
    .Q(net48),
    .CLK(clknet_3_6__leaf_clk));
 sg13g2_tiehi \u_core/_101__98  (.L_HI(net97));
 sg13g2_dfrbpq_1 \u_core/_102_  (.RESET_B(net96),
    .D(\u_core/_006_ ),
    .Q(net49),
    .CLK(clknet_3_7__leaf_clk));
 sg13g2_tiehi \u_core/_102__97  (.L_HI(net96));
 sg13g2_dfrbpq_1 \u_core/_103_  (.RESET_B(net95),
    .D(\u_core/_007_ ),
    .Q(net50),
    .CLK(clknet_3_4__leaf_clk));
 sg13g2_tiehi \u_core/_103__96  (.L_HI(net95));
 sg13g2_dfrbpq_1 \u_core/_104_  (.RESET_B(net94),
    .D(\u_core/_008_ ),
    .Q(net51),
    .CLK(clknet_3_1__leaf_clk));
 sg13g2_tiehi \u_core/_104__95  (.L_HI(net94));
 sg13g2_dfrbpq_1 \u_core/_105_  (.RESET_B(net93),
    .D(\u_core/_009_ ),
    .Q(net52),
    .CLK(clknet_3_7__leaf_clk));
 sg13g2_tiehi \u_core/_105__94  (.L_HI(net93));
 sg13g2_dfrbpq_1 \u_core/_106_  (.RESET_B(net92),
    .D(\u_core/_010_ ),
    .Q(net53),
    .CLK(clknet_3_1__leaf_clk));
 sg13g2_tiehi \u_core/_106__93  (.L_HI(net92));
 sg13g2_dfrbpq_1 \u_core/_107_  (.RESET_B(net91),
    .D(\u_core/_011_ ),
    .Q(net54),
    .CLK(clknet_3_5__leaf_clk));
 sg13g2_tiehi \u_core/_107__92  (.L_HI(net91));
 sg13g2_dfrbpq_1 \u_core/_108_  (.RESET_B(net90),
    .D(\u_core/_012_ ),
    .Q(net55),
    .CLK(clknet_3_4__leaf_clk));
 sg13g2_tiehi \u_core/_108__91  (.L_HI(net90));
 sg13g2_dfrbpq_1 \u_core/_109_  (.RESET_B(net89),
    .D(\u_core/_013_ ),
    .Q(net57),
    .CLK(clknet_3_3__leaf_clk));
 sg13g2_tiehi \u_core/_109__90  (.L_HI(net89));
 sg13g2_dfrbpq_1 \u_core/_110_  (.RESET_B(net88),
    .D(\u_core/_014_ ),
    .Q(net58),
    .CLK(clknet_3_3__leaf_clk));
 sg13g2_tiehi \u_core/_110__89  (.L_HI(net88));
 sg13g2_dfrbpq_1 \u_core/_111_  (.RESET_B(net87),
    .D(\u_core/_015_ ),
    .Q(net34),
    .CLK(clknet_3_0__leaf_clk));
 sg13g2_tiehi \u_core/_111__88  (.L_HI(net87));
 sg13g2_dfrbpq_1 \u_core/_112_  (.RESET_B(net86),
    .D(\u_core/_016_ ),
    .Q(net45),
    .CLK(clknet_3_5__leaf_clk));
 sg13g2_tiehi \u_core/_112__87  (.L_HI(net86));
 sg13g2_dfrbpq_1 \u_core/_113_  (.RESET_B(net85),
    .D(\u_core/_017_ ),
    .Q(net56),
    .CLK(clknet_3_2__leaf_clk));
 sg13g2_tiehi \u_core/_113__86  (.L_HI(net85));
 sg13g2_dfrbpq_1 \u_core/_114_  (.RESET_B(net84),
    .D(\u_core/_018_ ),
    .Q(net59),
    .CLK(clknet_3_5__leaf_clk));
 sg13g2_tiehi \u_core/_114__85  (.L_HI(net84));
 sg13g2_dfrbpq_1 \u_core/_115_  (.RESET_B(net83),
    .D(\u_core/_019_ ),
    .Q(net60),
    .CLK(clknet_3_2__leaf_clk));
 sg13g2_tiehi \u_core/_115__84  (.L_HI(net83));
 sg13g2_dfrbpq_1 \u_core/_116_  (.RESET_B(net82),
    .D(\u_core/_020_ ),
    .Q(net61),
    .CLK(clknet_3_6__leaf_clk));
 sg13g2_tiehi \u_core/_116__83  (.L_HI(net82));
 sg13g2_dfrbpq_1 \u_core/_117_  (.RESET_B(net81),
    .D(\u_core/_021_ ),
    .Q(net62),
    .CLK(clknet_3_0__leaf_clk));
 sg13g2_tiehi \u_core/_117__82  (.L_HI(net81));
 sg13g2_dfrbpq_1 \u_core/_118_  (.RESET_B(net80),
    .D(\u_core/_022_ ),
    .Q(net63),
    .CLK(clknet_3_6__leaf_clk));
 sg13g2_tiehi \u_core/_118__81  (.L_HI(net80));
 sg13g2_dfrbpq_1 \u_core/_119_  (.RESET_B(net79),
    .D(\u_core/_023_ ),
    .Q(net64),
    .CLK(clknet_3_1__leaf_clk));
 sg13g2_tiehi \u_core/_119__80  (.L_HI(net79));
 sg13g2_dfrbpq_1 \u_core/_120_  (.RESET_B(net78),
    .D(\u_core/_024_ ),
    .Q(net65),
    .CLK(clknet_3_5__leaf_clk));
 sg13g2_tiehi \u_core/_120__79  (.L_HI(net78));
 sg13g2_dfrbpq_1 \u_core/_121_  (.RESET_B(net77),
    .D(\u_core/_025_ ),
    .Q(net35),
    .CLK(clknet_3_6__leaf_clk));
 sg13g2_tiehi \u_core/_121__78  (.L_HI(net77));
 sg13g2_dfrbpq_1 \u_core/_122_  (.RESET_B(net76),
    .D(\u_core/_026_ ),
    .Q(net36),
    .CLK(clknet_3_0__leaf_clk));
 sg13g2_tiehi \u_core/_122__77  (.L_HI(net76));
 sg13g2_dfrbpq_1 \u_core/_123_  (.RESET_B(net75),
    .D(\u_core/_027_ ),
    .Q(net37),
    .CLK(clknet_3_7__leaf_clk));
 sg13g2_tiehi \u_core/_123__76  (.L_HI(net75));
 sg13g2_dfrbpq_1 \u_core/_124_  (.RESET_B(net74),
    .D(\u_core/_028_ ),
    .Q(net38),
    .CLK(clknet_3_2__leaf_clk));
 sg13g2_tiehi \u_core/_124__75  (.L_HI(net74));
 sg13g2_dfrbpq_1 \u_core/_125_  (.RESET_B(net73),
    .D(\u_core/_029_ ),
    .Q(net39),
    .CLK(clknet_3_7__leaf_clk));
 sg13g2_tiehi \u_core/_125__74  (.L_HI(net73));
 sg13g2_dfrbpq_1 \u_core/_126_  (.RESET_B(net72),
    .D(\u_core/_030_ ),
    .Q(net40),
    .CLK(clknet_3_1__leaf_clk));
 sg13g2_tiehi \u_core/_126__73  (.L_HI(net72));
 sg13g2_dfrbpq_1 \u_core/_127_  (.RESET_B(net71),
    .D(\u_core/_031_ ),
    .Q(net41),
    .CLK(clknet_3_0__leaf_clk));
 sg13g2_tiehi \u_core/_127__72  (.L_HI(net71));
 sg13g2_buf_1 \u_core/fanout66  (.A(\u_core/net67 ),
    .X(\u_core/net66 ));
 sg13g2_buf_1 \u_core/fanout67  (.A(\u_core/net70 ),
    .X(\u_core/net67 ));
 sg13g2_buf_1 \u_core/fanout68  (.A(\u_core/net70 ),
    .X(\u_core/net68 ));
 sg13g2_buf_1 \u_core/fanout69  (.A(\u_core/net70 ),
    .X(\u_core/net69 ));
 sg13g2_buf_1 \u_core/fanout70  (.A(net33),
    .X(\u_core/net70 ));
endmodule
