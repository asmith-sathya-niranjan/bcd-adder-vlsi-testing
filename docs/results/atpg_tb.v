`timescale 1ns/1ps
// Generated from ../atalanta/bcd_adder.test: applies the Atalanta ATPG patterns
// to bcd_adder.v and checks the expected outputs.
module atpg_tb;
  reg a0, a1, a2, a3, b0, b1, b2, b3, cin;
  wire s0, s1, s2, s3, cout;
  bcd_adder dut (.a0(a0), .a1(a1), .a2(a2), .a3(a3), .b0(b0), .b1(b1), .b2(b2), .b3(b3), .cin(cin), .s0(s0), .s1(s1), .s2(s2), .s3(s3), .cout(cout));
  integer errors = 0;
  task apply(input [8:0] pi, input [4:0] expect_po);
    begin
      {a0, a1, a2, a3, b0, b1, b2, b3, cin} = pi; #10;
      if ({s0, s1, s2, s3, cout} !== expect_po) begin
        errors = errors + 1;
        $display("MISMATCH: pi=%b got=%b expected=%b", pi, {s0, s1, s2, s3, cout}, expect_po);
      end
    end
  endtask
  initial begin
    apply(9'b000101010, 5'b00011);
    apply(9'b000000001, 5'b10000);
    apply(9'b010000010, 5'b00001);
    apply(9'b100000000, 5'b10000);
    apply(9'b001100100, 5'b01101);
    apply(9'b000000110, 5'b01001);
    apply(9'b011001000, 5'b00010);
    apply(9'b100010100, 5'b01100);
    apply(9'b000000010, 5'b00010);
    apply(9'b001100010, 5'b01011);
    apply(9'b110110010, 5'b01011);
    apply(9'b000100000, 5'b00010);
    apply(9'b000010000, 5'b10000);
    apply(9'b100000001, 5'b01000);
    $display("Atalanta patterns applied : 14");
    $display("Mismatches                : %0d", errors);
    if (errors == 0) $display("RESULT: PASS - ATPG patterns agree with the Verilog design");
    else $display("RESULT: FAIL");
    $finish;
  end
endmodule
