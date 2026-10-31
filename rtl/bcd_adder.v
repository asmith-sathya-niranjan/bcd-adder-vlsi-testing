// ============================================================
// 1-digit BCD adder, structural (gate-level) Verilog
//
//   Inputs : a3..a0  (BCD digit A, 0-9)
//            b3..b0  (BCD digit B, 0-9)
//            cin     (carry in from a previous digit)
//   Outputs: s3..s0  (BCD sum digit, 0-9)
//            cout    (decimal carry out)
//
// Algorithm
//   Stage 1: Z = A + B + Cin           (4-bit binary adder, carry K)
//   Stage 2: Cout = K | Z3.Z2 | Z3.Z1  (true when Z > 9)
//   Stage 3: S = Z + {0,Cout,Cout,0}   (add 6 when correction needed)
// ============================================================

// ---------- 1-bit full adder (gate primitives only) ----------
module full_adder (a, b, cin, sum, cout);
    input  a, b, cin;
    output sum, cout;
    wire   x1, c1, c2;

    xor g1 (x1,  a,  b);
    xor g2 (sum, x1, cin);
    and g3 (c1,  a,  b);
    and g4 (c2,  x1, cin);
    or  g5 (cout, c1, c2);
endmodule

// ---------- 1-bit half adder (gate primitives only) ----------
module half_adder (a, b, sum, cout);
    input  a, b;
    output sum, cout;

    xor g1 (sum,  a, b);
    and g2 (cout, a, b);
endmodule

// ---------- 1-digit BCD adder ----------
module bcd_adder (a0, a1, a2, a3,
                  b0, b1, b2, b3,
                  cin,
                  s0, s1, s2, s3,
                  cout);
    input  a0, a1, a2, a3;
    input  b0, b1, b2, b3;
    input  cin;
    output s0, s1, s2, s3;
    output cout;

    // stage 1 : binary ripple adder  Z = A + B + Cin
    wire z0, z1, z2, z3;
    wire k1, k2, k3, k4;          // k4 is the binary carry-out (K)

    full_adder FA0 (a0, b0, cin, z0, k1);
    full_adder FA1 (a1, b1, k1,  z1, k2);
    full_adder FA2 (a2, b2, k2,  z2, k3);
    full_adder FA3 (a3, b3, k3,  z3, k4);

    // stage 2 : "sum is greater than 9" detector
    wire t1, t2;
    and  U1 (t1, z3, z2);
    and  U2 (t2, z3, z1);
    or   U3 (cout, k4, t1, t2);

    // stage 3 : add 0110 when cout = 1
    //   bit0 : s0 = z0         (adding 0)
    //   bit1 : z1 + cout       (half adder)
    //   bit2 : z2 + cout + c1  (full adder)
    //   bit3 : z3 + c2         (final carry is discarded)
    wire c1, c2;

    buf  U4 (s0, z0);
    half_adder HA1 (z1, cout, s1, c1);
    full_adder FA5 (z2, cout, c1, s2, c2);
    xor  U5 (s3, z3, c2);
endmodule
