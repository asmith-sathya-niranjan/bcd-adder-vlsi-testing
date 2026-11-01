`timescale 1ns/1ps
// Fault simulation in the HDL simulator (works in Vivado xsim and Icarus):
// each wire of bcd_adder.v is forced to 0 / 1 (stuck-at fault), the Atalanta
// patterns are applied, and the outputs are compared with the healthy circuit.
module fault_demo_tb;
  reg a0,a1,a2,a3,b0,b1,b2,b3,cin;
  wire s0,s1,s2,s3,cout;
  bcd_adder dut(.a0(a0),.a1(a1),.a2(a2),.a3(a3),.b0(b0),.b1(b1),.b2(b2),.b3(b3),.cin(cin),
                .s0(s0),.s1(s1),.s2(s2),.s3(s3),.cout(cout));
  localparam N = 14;  localparam NF = 82;
  reg [8:0] P [0:N-1];
  reg [4:0] E [0:N-1];
  integer fst [0:NF-1];          // first detecting pattern (0 = never)
  reg [8*10-1:0] nm [0:NF-1];
  integer i, first, cnt, id, K, c70k;
  reg [4:0] got;
  task run(input [8*10-1:0] name);
    begin
      first = -1; cnt = 0;
      for (i = 0; i < N; i = i + 1) begin
        {a0,a1,a2,a3,b0,b1,b2,b3,cin} = P[i]; #5;
        got = {s0,s1,s2,s3,cout};
        if (got !== E[i]) begin cnt = cnt + 1; if (first < 0) first = i; end
      end
      nm[id] = name;
      if (first >= 0) begin
        fst[id] = first + 1;
        $display("%0s  DETECTED by %0d patterns, first at pattern #%0d (A=%0d B=%0d Cin=%0d)",
                 name, cnt, first+1, {P[first][5],P[first][6],P[first][7],P[first][8]},
                 {P[first][1],P[first][2],P[first][3],P[first][4]}, P[first][0]);
      end else begin
        fst[id] = 0;
        $display("%0s  not detected by this pattern set", name);
      end
      id = id + 1;
    end
  endtask
  function integer detected(input integer k);
    integer f;
    begin detected = 0;
      for (f = 0; f < NF; f = f + 1) if (fst[f] > 0 && fst[f] <= k) detected = detected + 1;
    end
  endfunction
  task report(input [8*4-1:0] label, input integer k);
    begin
      $display("%0s   patterns=%0d   detected=%0d of %0d   coverage=%0.2f %%   untested=%0d",
               label, k, detected(k), NF, 100.0*detected(k)/NF, NF - detected(k));
    end
  endtask
  integer f;
  initial begin
    id = 0;
    P[0] = 9'b000101010; E[0] = 5'b00011;
    P[1] = 9'b000000001; E[1] = 5'b10000;
    P[2] = 9'b010000010; E[2] = 5'b00001;
    P[3] = 9'b100000000; E[3] = 5'b10000;
    P[4] = 9'b001100100; E[4] = 5'b01101;
    P[5] = 9'b000000110; E[5] = 5'b01001;
    P[6] = 9'b011001000; E[6] = 5'b00010;
    P[7] = 9'b100010100; E[7] = 5'b01100;
    P[8] = 9'b000000010; E[8] = 5'b00010;
    P[9] = 9'b001100010; E[9] = 5'b01011;
    P[10] = 9'b110110010; E[10] = 5'b01011;
    P[11] = 9'b000100000; E[11] = 5'b00010;
    P[12] = 9'b000010000; E[12] = 5'b10000;
    P[13] = 9'b100000001; E[13] = 5'b01000;
    $display("Injecting 82 stuck-at faults into bcd_adder.v, applying 14 Atalanta patterns each");
    $display("------------------------------------------------------------------------");
    force dut.a0 = 1'b0; run("a0 /0    "); release dut.a0;
    force dut.a0 = 1'b1; run("a0 /1    "); release dut.a0;
    force dut.a1 = 1'b0; run("a1 /0    "); release dut.a1;
    force dut.a1 = 1'b1; run("a1 /1    "); release dut.a1;
    force dut.a2 = 1'b0; run("a2 /0    "); release dut.a2;
    force dut.a2 = 1'b1; run("a2 /1    "); release dut.a2;
    force dut.a3 = 1'b0; run("a3 /0    "); release dut.a3;
    force dut.a3 = 1'b1; run("a3 /1    "); release dut.a3;
    force dut.b0 = 1'b0; run("b0 /0    "); release dut.b0;
    force dut.b0 = 1'b1; run("b0 /1    "); release dut.b0;
    force dut.b1 = 1'b0; run("b1 /0    "); release dut.b1;
    force dut.b1 = 1'b1; run("b1 /1    "); release dut.b1;
    force dut.b2 = 1'b0; run("b2 /0    "); release dut.b2;
    force dut.b2 = 1'b1; run("b2 /1    "); release dut.b2;
    force dut.b3 = 1'b0; run("b3 /0    "); release dut.b3;
    force dut.b3 = 1'b1; run("b3 /1    "); release dut.b3;
    force dut.cin = 1'b0; run("cin /0   "); release dut.cin;
    force dut.cin = 1'b1; run("cin /1   "); release dut.cin;
    force dut.FA0.x1 = 1'b0; run("fa0_x /0 "); release dut.FA0.x1;
    force dut.FA0.x1 = 1'b1; run("fa0_x /1 "); release dut.FA0.x1;
    force dut.z0 = 1'b0; run("z0 /0    "); release dut.z0;
    force dut.z0 = 1'b1; run("z0 /1    "); release dut.z0;
    force dut.FA0.c1 = 1'b0; run("fa0_c1 /0"); release dut.FA0.c1;
    force dut.FA0.c1 = 1'b1; run("fa0_c1 /1"); release dut.FA0.c1;
    force dut.FA0.c2 = 1'b0; run("fa0_c2 /0"); release dut.FA0.c2;
    force dut.FA0.c2 = 1'b1; run("fa0_c2 /1"); release dut.FA0.c2;
    force dut.k1 = 1'b0; run("k1 /0    "); release dut.k1;
    force dut.k1 = 1'b1; run("k1 /1    "); release dut.k1;
    force dut.FA1.x1 = 1'b0; run("fa1_x /0 "); release dut.FA1.x1;
    force dut.FA1.x1 = 1'b1; run("fa1_x /1 "); release dut.FA1.x1;
    force dut.z1 = 1'b0; run("z1 /0    "); release dut.z1;
    force dut.z1 = 1'b1; run("z1 /1    "); release dut.z1;
    force dut.FA1.c1 = 1'b0; run("fa1_c1 /0"); release dut.FA1.c1;
    force dut.FA1.c1 = 1'b1; run("fa1_c1 /1"); release dut.FA1.c1;
    force dut.FA1.c2 = 1'b0; run("fa1_c2 /0"); release dut.FA1.c2;
    force dut.FA1.c2 = 1'b1; run("fa1_c2 /1"); release dut.FA1.c2;
    force dut.k2 = 1'b0; run("k2 /0    "); release dut.k2;
    force dut.k2 = 1'b1; run("k2 /1    "); release dut.k2;
    force dut.FA2.x1 = 1'b0; run("fa2_x /0 "); release dut.FA2.x1;
    force dut.FA2.x1 = 1'b1; run("fa2_x /1 "); release dut.FA2.x1;
    force dut.z2 = 1'b0; run("z2 /0    "); release dut.z2;
    force dut.z2 = 1'b1; run("z2 /1    "); release dut.z2;
    force dut.FA2.c1 = 1'b0; run("fa2_c1 /0"); release dut.FA2.c1;
    force dut.FA2.c1 = 1'b1; run("fa2_c1 /1"); release dut.FA2.c1;
    force dut.FA2.c2 = 1'b0; run("fa2_c2 /0"); release dut.FA2.c2;
    force dut.FA2.c2 = 1'b1; run("fa2_c2 /1"); release dut.FA2.c2;
    force dut.k3 = 1'b0; run("k3 /0    "); release dut.k3;
    force dut.k3 = 1'b1; run("k3 /1    "); release dut.k3;
    force dut.FA3.x1 = 1'b0; run("fa3_x /0 "); release dut.FA3.x1;
    force dut.FA3.x1 = 1'b1; run("fa3_x /1 "); release dut.FA3.x1;
    force dut.z3 = 1'b0; run("z3 /0    "); release dut.z3;
    force dut.z3 = 1'b1; run("z3 /1    "); release dut.z3;
    force dut.FA3.c1 = 1'b0; run("fa3_c1 /0"); release dut.FA3.c1;
    force dut.FA3.c1 = 1'b1; run("fa3_c1 /1"); release dut.FA3.c1;
    force dut.FA3.c2 = 1'b0; run("fa3_c2 /0"); release dut.FA3.c2;
    force dut.FA3.c2 = 1'b1; run("fa3_c2 /1"); release dut.FA3.c2;
    force dut.k4 = 1'b0; run("k4 /0    "); release dut.k4;
    force dut.k4 = 1'b1; run("k4 /1    "); release dut.k4;
    force dut.t1 = 1'b0; run("t1 /0    "); release dut.t1;
    force dut.t1 = 1'b1; run("t1 /1    "); release dut.t1;
    force dut.t2 = 1'b0; run("t2 /0    "); release dut.t2;
    force dut.t2 = 1'b1; run("t2 /1    "); release dut.t2;
    force dut.cout = 1'b0; run("cout /0  "); release dut.cout;
    force dut.cout = 1'b1; run("cout /1  "); release dut.cout;
    force dut.s0 = 1'b0; run("s0 /0    "); release dut.s0;
    force dut.s0 = 1'b1; run("s0 /1    "); release dut.s0;
    force dut.s1 = 1'b0; run("s1 /0    "); release dut.s1;
    force dut.s1 = 1'b1; run("s1 /1    "); release dut.s1;
    force dut.c1 = 1'b0; run("c1 /0    "); release dut.c1;
    force dut.c1 = 1'b1; run("c1 /1    "); release dut.c1;
    force dut.FA5.x1 = 1'b0; run("fa5_x /0 "); release dut.FA5.x1;
    force dut.FA5.x1 = 1'b1; run("fa5_x /1 "); release dut.FA5.x1;
    force dut.s2 = 1'b0; run("s2 /0    "); release dut.s2;
    force dut.s2 = 1'b1; run("s2 /1    "); release dut.s2;
    force dut.FA5.c1 = 1'b0; run("fa5_c1 /0"); release dut.FA5.c1;
    force dut.FA5.c1 = 1'b1; run("fa5_c1 /1"); release dut.FA5.c1;
    force dut.FA5.c2 = 1'b0; run("fa5_c2 /0"); release dut.FA5.c2;
    force dut.FA5.c2 = 1'b1; run("fa5_c2 /1"); release dut.FA5.c2;
    force dut.c2 = 1'b0; run("c2 /0    "); release dut.c2;
    force dut.c2 = 1'b1; run("c2 /1    "); release dut.c2;
    force dut.s3 = 1'b0; run("s3 /0    "); release dut.s3;
    force dut.s3 = 1'b1; run("s3 /1    "); release dut.s3;
    $display("------------------------------------------------------------------------");
    $display("FAULT COVERAGE EXPERIMENTS (stem faults only)");
    c70k = N;
    for (K = N; K >= 1; K = K - 1) if (100.0*detected(K)/NF >= 70.0) c70k = K;
    report("C70", c70k);
    report("HS", 1);
    report("GP", 5);
    report("MP", N);
    $display("Untested after GP (the hard faults):");
    for (f = 0; f < NF; f = f + 1) if (fst[f] == 0 || fst[f] > 5) $display("    %0s", nm[f]);
    $finish;
  end
endmodule
