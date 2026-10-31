#!/usr/bin/env python3
"""
fault_sim.py - small stuck-at fault simulator (substitute for the Modus
experiments when Modus is not available).

Usage:
    python3 fault_sim.py bcd_adder.bench bcd_adder.test [N_FULL]
    python3 fault_sim.py bcd_adder.bench bcd_adder.test --tb atpg_tb.v

What it does
  1. Builds the full (uncollapsed) stuck-at fault list of the .bench circuit
     (every signal and every fan-out branch, stuck-at-0 and stuck-at-1).
  2. Simulates all 2^n input combinations to find which faults are
     DETECTABLE and which are REDUNDANT (can never be detected).
  3. Fault-simulates the patterns Atalanta wrote in the .test file,
     one by one, and reports cumulative coverage.
  4. Prints the "C70", "HS", "GP", "MP" style experiments:
        C70 : fewest patterns that reach >= 70 % coverage
        HS  : first 1 pattern
        GP  : first N/3 patterns
        MP  : all N patterns
  5. With --tb FILE: writes a Verilog testbench that applies the Atalanta
     patterns to bcd_adder.v and checks the expected outputs
     (substitute for write_vectors -language verilog).
"""
import re
import sys
import itertools


# ------------------------------------------------------------------ parsing
def load_bench(path):
    inputs, outputs, gates = [], [], []      # gates: (name, type, [fanin])
    for line in open(path):
        line = line.split('#')[0].strip()
        if not line:
            continue
        m = re.match(r'INPUT\((\S+)\)', line)
        if m:
            inputs.append(m.group(1)); continue
        m = re.match(r'OUTPUT\((\S+)\)', line)
        if m:
            outputs.append(m.group(1)); continue
        m = re.match(r'(\S+)\s*=\s*(\w+)\((.*)\)', line)
        if m:
            gates.append((m.group(1), m.group(2).upper(),
                          [x.strip() for x in m.group(3).split(',')]))
    return inputs, outputs, gates


def load_patterns(path, n_in, n_out):
    pats = []
    for line in open(path):
        m = re.match(r'\s*\d+:\s*([01Xx]+)\s+([01Xx]+)\s*$', line)
        if m and len(m.group(1)) == n_in:
            pats.append(([0 if c in 'Xx' else int(c) for c in m.group(1)],
                         m.group(2)))
    return pats


# --------------------------------------------------------------- simulation
def gate_eval(t, x):
    if t == 'AND':  return int(all(x))
    if t == 'NAND': return int(not all(x))
    if t == 'OR':   return int(any(x))
    if t == 'NOR':  return int(not any(x))
    if t == 'XOR':  return sum(x) & 1
    if t == 'XNOR': return 1 - (sum(x) & 1)
    if t == 'NOT':  return 1 - x[0]
    if t in ('BUFF', 'BUF'): return x[0]
    raise ValueError('unknown gate type ' + t)


def simulate(ckt, vec, fault=None):
    """fault = None | ('stem', signal, sa) | ('branch', gate, pin, sa)"""
    inputs, outputs, gates = ckt
    v = dict(zip(inputs, vec))
    if fault and fault[0] == 'stem' and fault[1] in v:
        v[fault[1]] = fault[2]
    for name, t, fin in gates:
        x = [v[s] for s in fin]
        if fault and fault[0] == 'branch' and fault[1] == name:
            x[fault[2]] = fault[3]
        r = gate_eval(t, x)
        if fault and fault[0] == 'stem' and fault[1] == name:
            r = fault[2]
        v[name] = r
    return ''.join(str(v[o]) for o in outputs)


def build_fault_list(ckt):
    inputs, outputs, gates = ckt
    fanout = {}
    for name, t, fin in gates:
        for s in fin:
            fanout[s] = fanout.get(s, 0) + 1
    faults = []
    for s in inputs + [g[0] for g in gates]:
        for sa in (0, 1):
            faults.append(('stem', s, sa))
    for name, t, fin in gates:
        for pin, s in enumerate(fin):
            if fanout[s] > 1:                 # real fan-out branch
                for sa in (0, 1):
                    faults.append(('branch', name, pin, sa))
    return faults


def fname(f):
    if f[0] == 'stem':
        return '%s /%d' % (f[1], f[2])
    return 'input pin %d of %s /%d' % (f[2], f[1], f[3])


# -------------------------------------------------------------------- main
def main():
    args = sys.argv[1:]
    tb_file = None
    if '--tb' in args:
        i = args.index('--tb'); tb_file = args[i + 1]; del args[i:i + 2]
    if len(args) < 2:
        print(__doc__); sys.exit(1)
    bench, testfile = args[0], args[1]
    ckt = load_bench(bench)
    inputs, outputs, gates = ckt
    pats = load_patterns(testfile, len(inputs), len(outputs))
    n = len(pats)
    n_full = int(args[2]) if len(args) > 2 else n

    faults = build_fault_list(ckt)
    good = {vec: simulate(ckt, vec)
            for vec in itertools.product((0, 1), repeat=len(inputs))}

    # 1+2: exhaustive classification
    detectable, redundant = [], []
    for f in faults:
        hit = any(simulate(ckt, vec, f) != good[vec] for vec in good)
        (detectable if hit else redundant).append(f)

    print('=' * 62)
    print(' FAULT SIMULATION REPORT  (%s)' % bench)
    print('=' * 62)
    print(' Inputs / outputs / gates            : %d / %d / %d'
          % (len(inputs), len(outputs), len(gates)))
    print(' Total stuck-at faults (uncollapsed) : %d' % len(faults))
    print(' Detectable faults                   : %d' % len(detectable))
    print(' Redundant faults (undetectable)     : %d' % len(redundant))
    for f in redundant:
        print('     redundant: ' + fname(f))
    print(' Max attainable fault coverage       : %.3f %%'
          % (100.0 * len(detectable) / len(faults)))
    print(' Atalanta patterns read from %s : %d' % (testfile, n))

    # 3: cumulative coverage
    remaining = list(detectable)
    cum = []                       # (pattern#, detected so far, coverage %)
    done = 0
    for k, (vec, resp) in enumerate(pats, 1):
        still = []
        for f in remaining:
            if simulate(ckt, vec, f) != good[tuple(vec)]:
                done += 1
            else:
                still.append(f)
        remaining = still
        cum.append((k, done, 100.0 * done / len(faults)))

    print('\n Cumulative coverage of the Atalanta patterns')
    print(' ' + '-' * 44)
    print(' %-9s %-10s %-10s' % ('Patterns', 'Detected', 'Coverage'))
    for k, d, c in cum:
        print(' %-9d %-10d %7.2f %%' % (k, d, c))

    def row(label, k):
        k = max(1, min(k, n))
        _, d, c = cum[k - 1]
        return (label, k, d, c, len(faults) - d, c / k)

    # 4: experiments
    c70 = next((k for k, d, c in cum if c >= 70.0), n)
    rows = [row('C70', c70),
            row('HS', 1),
            row('GP', max(1, round(n_full / 3))),
            row('MP', n)]
    print('\n Experiments (same idea as the Modus HS / GP / MP / C70 runs)')
    print(' ' + '-' * 66)
    print(' %-5s %-9s %-9s %-10s %-10s %-14s'
          % ('Mode', 'Patterns', 'Detected', 'Coverage', 'Untested',
             'Efficiency'))
    for label, k, d, c, u, e in rows:
        print(' %-5s %-9d %-9d %7.2f %%  %-10d %.2f %%/pattern'
              % (label, k, d, c, u, e))
    print(' Efficiency here = coverage % / number of patterns')
    print(' (this circuit is far too small for CPU time to be measurable).')

    # 5: Verilog testbench from the Atalanta patterns
    if tb_file:
        with open(tb_file, 'w') as fh:
            fh.write('`timescale 1ns/1ps\n')
            fh.write('// Generated from %s: applies the Atalanta ATPG patterns\n'
                     % testfile)
            fh.write('// to bcd_adder.v and checks the expected outputs.\n')
            fh.write('module atpg_tb;\n')
            fh.write('  reg %s;\n' % ', '.join(inputs))
            fh.write('  wire %s;\n' % ', '.join(outputs))
            conn = ', '.join('.%s(%s)' % (s, s) for s in inputs + outputs)
            fh.write('  bcd_adder dut (%s);\n' % conn)
            fh.write('  integer errors = 0;\n')
            fh.write('  task apply(input [%d:0] pi, input [%d:0] expect_po);\n'
                     % (len(inputs) - 1, len(outputs) - 1))
            fh.write('    begin\n')
            fh.write('      {%s} = pi; #10;\n' % ', '.join(inputs))
            fh.write('      if ({%s} !== expect_po) begin\n' % ', '.join(outputs))
            fh.write('        errors = errors + 1;\n')
            fh.write('        $display("MISMATCH: pi=%b got=%b expected=%b", '
                     'pi, {' + ', '.join(outputs) + '}, expect_po);\n')
            fh.write('      end\n    end\n  endtask\n')
            fh.write('  initial begin\n')
            for vec, resp in pats:
                fh.write("    apply(%d'b%s, %d'b%s);\n"
                         % (len(inputs), ''.join(map(str, vec)),
                            len(outputs), resp))
            fh.write('    $display("Atalanta patterns applied : %d");\n' % n)
            fh.write('    $display("Mismatches                : %0d", errors);\n')
            fh.write('    if (errors == 0) $display("RESULT: PASS - ATPG patterns '
                     'agree with the Verilog design");\n')
            fh.write('    else $display("RESULT: FAIL");\n')
            fh.write('    $finish;\n  end\nendmodule\n')
        print('\n Wrote Verilog testbench: %s' % tb_file)


if __name__ == '__main__':
    main()
