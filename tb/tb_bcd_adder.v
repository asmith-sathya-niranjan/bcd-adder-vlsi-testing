`timescale 1ns/1ps
// Exhaustive self-checking testbench:
// every valid BCD input (A=0..9, B=0..9, Cin=0..1) = 200 cases
module tb_bcd_adder;
    reg  [3:0] A, B;
    reg        cin;
    wire [3:0] S;
    wire       cout;

    integer i, j, c;
    integer errors, tests;
    integer total, exp_digit, exp_carry;

    bcd_adder dut (.a0(A[0]), .a1(A[1]), .a2(A[2]), .a3(A[3]),
                   .b0(B[0]), .b1(B[1]), .b2(B[2]), .b3(B[3]),
                   .cin(cin),
                   .s0(S[0]), .s1(S[1]), .s2(S[2]), .s3(S[3]),
                   .cout(cout));

    initial begin
        errors = 0;
        tests  = 0;
        for (i = 0; i <= 9; i = i + 1)
            for (j = 0; j <= 9; j = j + 1)
                for (c = 0; c <= 1; c = c + 1) begin
                    A = i; B = j; cin = c;
                    #10;
                    total     = i + j + c;
                    exp_digit = total % 10;
                    exp_carry = total / 10;
                    tests = tests + 1;
                    if (S !== exp_digit[3:0] || cout !== exp_carry[0]) begin
                        errors = errors + 1;
                        $display("FAIL: %0d + %0d + %0d -> got carry=%b digit=%0d, expected carry=%0d digit=%0d",
                                 i, j, c, cout, S, exp_carry, exp_digit);
                    end
                end

        $display("--------------------------------------------");
        $display("Tests run : %0d", tests);
        $display("Errors    : %0d", errors);
        if (errors == 0) $display("RESULT: PASS - BCD adder is correct");
        else             $display("RESULT: FAIL");
        $finish;
    end


    // waveform file (optional: open with gtkwave)
    initial begin
        $dumpfile("bcd_adder.vcd");
        $dumpvars(0, tb_bcd_adder);
    end
endmodule
