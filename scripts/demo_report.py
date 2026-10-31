#!/usr/bin/env python3
"""
demo_report.py - turns the Atalanta results into something you can SHOW.

Usage (same folder as fault_sim.py):
    python3 demo_report.py bcd_adder.bench bcd_adder.test

Creates
    demo_report.html    open in a browser (or Print -> Save as PDF)
    fault_demo_tb.v     Verilog testbench that injects faults into
                        bcd_adder.v and runs the Atalanta patterns

and prints the main tables in the terminal.
"""
import sys
import html
import itertools
from fault_sim import load_bench, load_patterns, build_fault_list, simulate, fname

NETS_IN_VERILOG = {'z0', 'z1', 'z2', 'z3', 'k1', 'k2', 'k3', 'k4', 't1', 't2',
                   'c1', 'c2', 's0', 's1', 's2', 's3', 'cout'}


def dec_in(vec):
    A = sum(vec[i] << i for i in range(4))
    B = sum(vec[4 + i] << i for i in range(4))
    return A, B, vec[8]


def dec_out(resp):                       # resp order: s0 s1 s2 s3 cout
    return int(resp[4]), int(resp[3] + resp[2] + resp[1] + resp[0], 2)


def show_out(resp):
    c, d = dec_out(resp)
    return 'carry %d, digit %d' % (c, d)


def valid(A, B):
    return A <= 9 and B <= 9


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    bench, testfile = sys.argv[1], sys.argv[2]
    ckt = load_bench(bench)
    inputs, outputs, gates = ckt
    pats = load_patterns(testfile, len(inputs), len(outputs))
    n = len(pats)
    faults = build_fault_list(ckt)
    allvec = list(itertools.product((0, 1), repeat=len(inputs)))
    good = {v: simulate(ckt, v) for v in allvec}

    # ---- fault simulation: per pattern detections + exhaustive count ----
    pat_det = [set() for _ in pats]
    count = []
    for fi, f in enumerate(faults):
        count.append(sum(simulate(ckt, v, f) != good[v] for v in allvec))
        for k, (vec, _) in enumerate(pats):
            if simulate(ckt, tuple(vec), f) != good[tuple(vec)]:
                pat_det[k].add(fi)
    redundant = [fi for fi, c in enumerate(count) if c == 0]
    first = {}                      # fault index -> first pattern index
    for k in range(n):
        for fi in pat_det[k]:
            first.setdefault(fi, k)
    seen, cum, new_at = set(), [], []
    for k in range(n):
        new = pat_det[k] - seen
        seen |= pat_det[k]
        new_at.append(len(new))
        cum.append(100.0 * len(seen) / len(faults))
    tot = len(faults)

    # which faults can be caught using VALID BCD inputs only?
    vfirst, nvalid, vdet = {}, [], []
    vvecs = [tuple([(A >> i) & 1 for i in range(4)] + [(B >> i) & 1 for i in range(4)] + [c])
             for A in range(10) for B in range(10) for c in (0, 1)]
    for fi, f in enumerate(faults):
        hit = set()
        for j, vec in enumerate(vvecs):
            if simulate(ckt, vec, f) != good[vec]:
                hit.add(j)
                vfirst.setdefault(fi, vec)
        vdet.append(hit)
        nvalid.append(len(hit))
    n_det = sum(1 for c in count if c)
    n_valid = len(vfirst)
    n_only_nonbcd = n_det - n_valid
    # greedy small test set that uses ONLY valid BCD inputs
    remaining = {fi for fi in range(tot) if vdet[fi]}
    bcd_set = []
    while remaining:
        bj = max(range(len(vvecs)), key=lambda j: sum(1 for fi in remaining if j in vdet[fi]))
        gain = {fi for fi in remaining if bj in vdet[fi]}
        bcd_set.append((bj, len(gain)))
        remaining -= gain
    bcd_cov = 100.0 * n_valid / tot

    def evidence(fi, vec=None):
        k = first.get(fi, -1)
        if vec is None:
            vec = tuple(pats[k][0])
        fo = simulate(ckt, vec, faults[fi])
        go = good[vec]
        diff = [outputs[i] for i in range(len(outputs)) if fo[i] != go[i]]
        return k, vec, go, fo, diff

    def pick(fi):           # prefer an input that is a valid BCD addition
        if fi in vfirst:
            return vfirst[fi], 'valid BCD input'
        return tuple(pats[first[fi]][0]), 'Atalanta pattern #%d (not valid BCD)' % (first[fi] + 1)

    # ---------------------------------------------------------- terminal
    print('=' * 70)
    print(' ATALANTA PATTERNS DECODED  (%s)' % bench)
    print('=' * 70)
    print(' %-3s %-3s %-3s %-4s %-26s %-9s %s'
          % ('#', 'A', 'B', 'Cin', 'Expected output', 'New faults', 'Coverage'))
    for k, (vec, resp) in enumerate(pats):
        A, B, c = dec_in(vec)
        tag = '' if valid(A, B) else '  (not valid BCD)'
        print(' %-3d %-3d %-3d %-4d %-26s %-9d %6.2f %%%s'
              % (k + 1, A, B, c, show_out(resp), new_at[k], cum[k], tag))
    print('\n Redundant (never detectable): %s'
          % (', '.join(fname(faults[i]) for i in redundant) or 'none'))
    print('\n WORKED EXAMPLES: how a fault shows up at the outputs')
    print(' ' + '-' * 68)
    want = ['z1 /0', 'k2 /1', 'cout /0', 'c2 /1', 's3 /0', 's1 /1']
    names = {fname(f): i for i, f in enumerate(faults)}
    ex = [names[w] for w in want if w in names and names[w] in first]
    if len(ex) < 4:
        ex = list(first)[:5]
    for fi in ex:
        vec, src = pick(fi)
        k, vec, go, fo, diff = evidence(fi, vec)
        A, B, c = dec_in(vec)
        print(' Fault %-12s test input: A=%d B=%d Cin=%d  [%s]'
              % (fname(faults[fi]), A, B, c, src))
        print('    fault-free : %s   (%d + %d + %d = %d)'
              % (show_out(go), A, B, c, A + B + c))
        print('    with fault : %s' % show_out(fo))
        print('    outputs that differ: %s  -> FAULT DETECTED\n' % ', '.join(diff))
    if n_only_nonbcd == 0:
        print(' All %d detectable faults can be caught with VALID BCD inputs only.' % n_det)
    else:
        print(' %d of %d detectable faults can be caught with valid BCD inputs only;' % (n_valid, n_det))
        print(' the other %d need an input with a digit above 9.' % n_only_nonbcd)
    print('\n BCD-ONLY TEST SET (greedy): %d patterns reach %.2f %% coverage' % (len(bcd_set), bcd_cov))
    for i, (j, g) in enumerate(bcd_set):
        A, B, c = dec_in(vvecs[j])
        print('   %2d. %d + %d + %d = %-2d  -> %-20s new faults: %d'
              % (i + 1, A, B, c, A + B + c, show_out(good[vvecs[j]]), g))
    print()

    # ------------------------------------------------------- HTML report
    H = []
    w = H.append
    w('<!doctype html><html><head><meta charset="utf-8"><title>BCD adder - test report</title><style>')
    w('body{font:15px/1.5 system-ui,Segoe UI,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;color:#16202e}'
      'h1{margin-bottom:0}h2{margin-top:34px;border-bottom:2px solid #1d4ed8;padding-bottom:4px}'
      'table{border-collapse:collapse;margin:10px 0;font-size:14px}td,th{border:1px solid #bcc7d6;padding:4px 8px;text-align:center}'
      'th{background:#e8eef7}code,.m{font-family:Consolas,monospace}.grid td{width:34px}'
      '.corr{background:#fff3cd}.bad{background:#f8c9d0;font-weight:700}.ok{color:#0f7a55;font-weight:700}'
      '.no{color:#b3261e;font-weight:700}.diff{background:#f8c9d0;font-weight:700}'
      '.card{border:1px solid #bcc7d6;border-radius:8px;padding:10px 14px;margin:10px 0;break-inside:avoid}'
      '.note{color:#4b5a6e}@media print{h2{break-after:avoid}}')
    w('</style></head><body>')
    w('<h1>1-digit BCD adder: design verification and fault testing</h1>')
    w('<p class="note">Circuit file: %s &nbsp;|&nbsp; %d inputs, %d outputs, %d gates &nbsp;|&nbsp; '
      '%d stuck-at faults &nbsp;|&nbsp; ATPG: Atalanta, patterns: %d</p>'
      % (html.escape(bench), len(inputs), len(outputs), len(gates), tot, n))

    w('<h2>1. Proof that the circuit is a BCD adder</h2>')
    w('<p>Inputs: digit A (a3..a0), digit B (b3..b0) and carry in. Outputs: digit S (s3..s0) and carry out. '
      'Every cell below is the value <b>produced by the gate-level circuit</b> (carry and digit read together) '
      'for that A (row) and B (column). Yellow cells are the ones where the sum exceeded 9, so the +0110 correction was used.</p>')
    allok = True
    for cin in (0, 1):
        w('<b>Carry in = %d</b><table class="grid"><tr><th>A \\ B</th>%s</tr>'
          % (cin, ''.join('<th>%d</th>' % b for b in range(10))))
        for a in range(10):
            w('<tr><th>%d</th>' % a)
            for b in range(10):
                vec = tuple([(a >> i) & 1 for i in range(4)] + [(b >> i) & 1 for i in range(4)] + [cin])
                c, d = dec_out(simulate(ckt, vec))
                got, exp = c * 10 + d, a + b + cin
                allok &= (got == exp)
                cls = 'bad' if got != exp else ('corr' if exp > 9 else '')
                w('<td class="%s">%d</td>' % (cls, got))
            w('</tr>')
        w('</table>')
    w('<p class="%s">%s</p>' % ('ok' if allok else 'no',
      'All 200 valid BCD inputs give the correct decimal result.' if allok else 'MISMATCH FOUND'))
    w('<p class="note">Example: A=9, B=9, Cin=1 gives 19: the binary adder makes 10011, the detector sees '
      'Z &gt; 9, and adding 0110 gives digit 1001 (9) with carry out 1.</p>')

    w('<h2>2. Test patterns generated by Atalanta</h2>')
    w('<p>Each row is one input combination applied to the circuit, the output a healthy circuit must give, '
      'how many <i>new</i> faults it uncovers, and the running fault coverage. '
      'Rows marked "not valid BCD" use a digit above 9: the ATPG tool sees only gates, not BCD rules.</p>')
    w('<table><tr><th>#</th><th>A</th><th>B</th><th>Cin</th><th>Raw inputs a0..a3 b0..b3 cin</th>'
      '<th>Expected output</th><th>Raw outputs s0..s3 cout</th><th>New faults</th><th>Coverage</th></tr>')
    for k, (vec, resp) in enumerate(pats):
        A, B, c = dec_in(vec)
        w('<tr><td>%d</td><td>%d</td><td>%d</td><td>%d</td><td class="m">%s</td><td>%s%s</td><td class="m">%s</td>'
          '<td>%d</td><td>%.2f %%</td></tr>'
          % (k + 1, A, B, c, ''.join(map(str, vec)), show_out(resp),
             '' if valid(A, B) else ' <i>(not valid BCD)</i>', resp, new_at[k], cum[k]))
    w('</table>')

    w('<h2>3. How a fault is detected: compare healthy and faulty outputs</h2>')
    w('<p>A stuck-at fault forces one wire to a constant 0 or 1. A test pattern <b>detects</b> the fault when at least one '
      'output of the faulty circuit differs from the healthy circuit. Highlighted outputs are where the difference appears.</p>')
    for fi in ex:
        vec, src = pick(fi)
        k, vec, go, fo, diff = evidence(fi, vec)
        A, B, c = dec_in(vec)
        w('<div class="card"><b>Fault: %s</b> (wire stuck at a constant). Test input: '
          'A=%d, B=%d, Cin=%d (%s), so the correct answer is %d.'
          % (html.escape(fname(faults[fi])), A, B, c, src, A + B + c))
        w('<table><tr><th></th>%s<th>Decoded</th></tr>' % ''.join('<th>%s</th>' % o for o in outputs))
        w('<tr><td>Healthy</td>%s<td>%s</td></tr>' % (''.join('<td class="m">%s</td>' % ch for ch in go), show_out(go)))
        w('<tr><td>Faulty</td>%s<td>%s</td></tr></table>'
          % (''.join('<td class="m%s">%s</td>' % (' diff' if go[i] != fo[i] else '', fo[i]) for i in range(len(fo))),
             show_out(fo)))
        w('<span class="ok">Outputs that differ: %s, so the fault is detected.</span></div>' % ', '.join(diff))
    if n_only_nonbcd == 0:
        w('<p><b>Functional vs structural testing:</b> all %d detectable faults can be caught using only valid BCD inputs '
          '(digits 0 to 9). Atalanta also used some inputs with a digit above 9 because an ATPG tool sees only gates, '
          'not BCD rules, but they are not needed: the circuit can be fully tested through its normal BCD operation.</p>' % n_det)
    else:
        w('<p><b>Functional vs structural testing:</b> %d of the %d detectable faults can be caught using only valid BCD '
          'inputs; the other %d need an input with a digit above 9.</p>' % (n_valid, n_det, n_only_nonbcd))
    w('<h3>A compact test set using only valid BCD inputs (%d patterns, %.2f %% coverage)</h3>' % (len(bcd_set), bcd_cov))
    w('<table><tr><th>#</th><th>A</th><th>B</th><th>Cin</th><th>Correct result</th><th>Circuit output</th><th>New faults</th></tr>')
    for i, (j, g) in enumerate(bcd_set):
        A, B, c = dec_in(vvecs[j])
        w('<tr><td>%d</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td><td>%s</td><td>%d</td></tr>'
          % (i + 1, A, B, c, A + B + c, show_out(good[vvecs[j]]), g))
    w('</table>')
    if redundant:
        for fi in redundant:
            w('<div class="card"><b>Fault: %s</b>: tried against all 512 input combinations, '
              '<span class="no">no input ever changes an output</span>. This is a <b>redundant</b> fault: it cannot be '
              'detected by any test, so it lowers fault coverage but not test quality. '
              'Simplifying the logic (bcd_adder_opt.bench) removes it.</div>' % html.escape(fname(faults[fi])))

    w('<h2>4. Coverage experiments (Modus-style HS / GP / MP / C70)</h2>')
    c70 = next((k + 1 for k in range(n) if cum[k] >= 70), n)
    rows = [('C70', c70), ('HS', 1), ('GP', max(1, round(n / 3))), ('MP', n)]
    w('<table><tr><th>Mode</th><th>Patterns</th><th>Coverage</th><th>Untested faults</th><th>Coverage per pattern</th></tr>')
    for lab, k in rows:
        undet = tot - round(cum[k - 1] * tot / 100)
        w('<tr><td>%s</td><td>%d</td><td>%.2f %%</td><td>%d</td><td>%.2f %%</td></tr>'
          % (lab, k, cum[k - 1], undet, cum[k - 1] / k))
    w('</table><p class="note">C70: fewest patterns reaching 70 %. HS: first pattern only. GP: one third of the set. MP: the whole set.</p>')

    w('<h2>5. Every fault: which pattern catches it, and where it shows</h2>')
    w('<table><tr><th>Fault</th><th>First pattern</th><th>A</th><th>B</th><th>Cin</th><th>Healthy</th><th>Faulty</th>'
      '<th>Differing outputs</th><th>Detected by (of 512)</th><th>Valid-BCD input that detects it</th></tr>')
    for fi, f in enumerate(faults):
        if fi in first:
            k, vec, go, fo, diff = evidence(fi)
            A, B, c = dec_in(vec)
            vtxt = ('A=%d B=%d Cin=%d' % dec_in(vfirst[fi])) if fi in vfirst else '<i>none</i>'
            w('<tr><td class="m">%s</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%d</td><td>%s</td></tr>'
              % (html.escape(fname(f)), k + 1, A, B, c, show_out(go), show_out(fo), ', '.join(diff), count[fi], vtxt))
        else:
            w('<tr><td class="m">%s</td><td colspan="7" class="no">%s</td><td>%d</td><td></td></tr>'
              % (html.escape(fname(f)), 'redundant: never detectable' if count[fi] == 0 else 'not hit by this pattern set', count[fi]))
    w('</table></body></html>')
    open('demo_report.html', 'w', encoding='utf-8').write('\n'.join(H))
    print(' Wrote demo_report.html  (open it in your browser)')

    # ------------------------------------------- Verilog fault injection
    # Every stem (wire) fault of the netlist is forced inside bcd_adder.v.
    # Branch faults cannot be forced from outside a netlist, so they are not included.
    import re
    def vpath(name):
        m = re.match(r'fa(\d)_(x|c1|c2)$', name)
        if m:
            return 'dut.FA%s.%s' % (m.group(1), 'x1' if m.group(2) == 'x' else m.group(2))
        return 'dut.' + name
    stem = [f for f in faults if f[0] == 'stem']
    NF = len(stem)
    gp_k = max(1, round(n / 3))
    V = ['`timescale 1ns/1ps',
         '// Fault simulation in the HDL simulator (works in Vivado xsim and Icarus):',
         '// each wire of bcd_adder.v is forced to 0 / 1 (stuck-at fault), the Atalanta',
         '// patterns are applied, and the outputs are compared with the healthy circuit.',
         'module fault_demo_tb;',
         '  reg a0,a1,a2,a3,b0,b1,b2,b3,cin;',
         '  wire s0,s1,s2,s3,cout;',
         '  bcd_adder dut(.a0(a0),.a1(a1),.a2(a2),.a3(a3),.b0(b0),.b1(b1),.b2(b2),.b3(b3),.cin(cin),',
         '                .s0(s0),.s1(s1),.s2(s2),.s3(s3),.cout(cout));',
         '  localparam N = %d;  localparam NF = %d;' % (n, NF),
         '  reg [8:0] P [0:N-1];',
         '  reg [4:0] E [0:N-1];',
         '  integer fst [0:NF-1];          // first detecting pattern (0 = never)',
         '  reg [8*10-1:0] nm [0:NF-1];',
         '  integer i, first, cnt, id, K, c70k;',
         '  reg [4:0] got;',
         '  task run(input [8*10-1:0] name);',
         '    begin',
         '      first = -1; cnt = 0;',
         '      for (i = 0; i < N; i = i + 1) begin',
         '        {a0,a1,a2,a3,b0,b1,b2,b3,cin} = P[i]; #5;',
         '        got = {s0,s1,s2,s3,cout};',
         '        if (got !== E[i]) begin cnt = cnt + 1; if (first < 0) first = i; end',
         '      end',
         '      nm[id] = name;',
         '      if (first >= 0) begin',
         '        fst[id] = first + 1;',
         '        $display("%0s  DETECTED by %0d patterns, first at pattern #%0d (A=%0d B=%0d Cin=%0d)",',
         '                 name, cnt, first+1, {P[first][5],P[first][6],P[first][7],P[first][8]},',
         '                 {P[first][1],P[first][2],P[first][3],P[first][4]}, P[first][0]);',
         '      end else begin',
         '        fst[id] = 0;',
         '        $display("%0s  not detected by this pattern set", name);',
         '      end',
         '      id = id + 1;',
         '    end',
         '  endtask',
         '  function integer detected(input integer k);',
         '    integer f;',
         '    begin detected = 0;',
         '      for (f = 0; f < NF; f = f + 1) if (fst[f] > 0 && fst[f] <= k) detected = detected + 1;',
         '    end',
         '  endfunction',
         '  task report(input [8*4-1:0] label, input integer k);',
         '    begin',
         '      $display("%0s   patterns=%0d   detected=%0d of %0d   coverage=%0.2f %%   untested=%0d",',
         '               label, k, detected(k), NF, 100.0*detected(k)/NF, NF - detected(k));',
         '    end',
         '  endtask',
         '  integer f;',
         '  initial begin',
         '    id = 0;']
    for k, (vec, resp) in enumerate(pats):
        V.append("    P[%d] = 9'b%s; E[%d] = 5'b%s;" % (k, ''.join(map(str, vec)), k, resp))
    V.append('    $display("Injecting %d stuck-at faults into bcd_adder.v, applying %d Atalanta patterns each");' % (NF, n))
    V.append('    $display("------------------------------------------------------------------------");')
    for f in stem:
        V.append('    force %s = 1\'b%d; run("%s"); release %s;'
                 % (vpath(f[1]), f[2], ('%s /%d' % (f[1], f[2])).ljust(9), vpath(f[1])))
    V.append('    $display("------------------------------------------------------------------------");')
    V.append('    $display("FAULT COVERAGE EXPERIMENTS (stem faults only)");')
    V.append('    c70k = N;')
    V.append('    for (K = N; K >= 1; K = K - 1) if (100.0*detected(K)/NF >= 70.0) c70k = K;')
    V.append('    report("C70", c70k);')
    V.append('    report("HS", 1);')
    V.append('    report("GP", %d);' % gp_k)
    V.append('    report("MP", N);')
    V.append('    $display("Untested after GP (the hard faults):");')
    V.append('    for (f = 0; f < NF; f = f + 1) if (fst[f] == 0 || fst[f] > %d) $display("    %%0s", nm[f]);' % gp_k)
    V.append('    $finish;')
    V.append('  end')
    V.append('endmodule')
    open('fault_demo_tb.v', 'w').write('\n'.join(V) + '\n')
    print(' Wrote fault_demo_tb.v   (%d wire faults; run: iverilog -o fd.out bcd_adder.v fault_demo_tb.v ; vvp fd.out)' % NF)


if __name__ == '__main__':
    main()
