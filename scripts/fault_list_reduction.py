#!/usr/bin/env python3
"""
fault_list_reduction.py  -  FAULT LIST REDUCTION for a .bench circuit (CO2)

usage:  python3 fault_list_reduction.py bcd_adder.bench

Stages (each one makes the fault list shorter):
  0. FULL list        : stuck-at-0 / stuck-at-1 on every input, every gate output
                        and every gate input pin.
  1. STRUCTURAL       : equivalence collapsing by gate rules (no simulation needed)
                          AND / NAND : any input SA0 == output SA0 (SA1 for NAND)
                          OR  / NOR  : any input SA1 == output SA1 (SA0 for NOR)
                          NOT / BUFF : input fault == output fault
                          a wire with one fan-out : stem fault == pin fault
  2. REDUNDANT        : exhaustive simulation; a fault that no input can detect is removed
  3. FUNCTIONAL       : faults that give identical outputs for ALL inputs are merged

Writes (in the current folder):
  <name>_full.flt  <name>_collapsed.flt   fault lists in ATALANTA format  (use with  atalanta -f)
  <name>_redundant.txt                    the redundant faults
  <name>_fault_list_reduction.png         bar graph of the four stages
"""
import re, sys, itertools, os

# ------------------------------------------------------------ read the circuit
def load_bench(path):
    inputs, outputs, gates = [], [], []          # gates: (name, TYPE, [fan-in names])
    for line in open(path):
        line = line.split('#')[0].strip()
        if not line: continue
        m = re.match(r'INPUT\((\S+)\)', line)
        if m: inputs.append(m.group(1)); continue
        m = re.match(r'OUTPUT\((\S+)\)', line)
        if m: outputs.append(m.group(1)); continue
        m = re.match(r'(\S+)\s*=\s*(\w+)\((.*)\)', line)
        if m: gates.append((m.group(1), m.group(2).upper(), [x.strip() for x in m.group(3).split(',')]))
    return inputs, outputs, gates

def gate_eval(t, x):
    if t == 'AND':  return int(all(x))
    if t == 'NAND': return int(not all(x))
    if t == 'OR':   return int(any(x))
    if t == 'NOR':  return int(not any(x))
    if t == 'XOR':  return sum(x) & 1
    if t == 'XNOR': return 1 - (sum(x) & 1)
    if t == 'NOT':  return 1 - x[0]
    return x[0]                                    # BUFF / BUF

# fault = ('stem', signal, sa)  or  ('pin', gate, pin_index, sa)
def simulate(ckt, vec, fault=None):
    inputs, outputs, gates = ckt
    v = dict(zip(inputs, vec))
    if fault and fault[0] == 'stem' and fault[1] in v: v[fault[1]] = fault[2]
    for name, t, fin in gates:
        x = [v[s] for s in fin]
        if fault and fault[0] == 'pin' and fault[1] == name: x[fault[2]] = fault[3]
        r = gate_eval(t, x)
        if fault and fault[0] == 'stem' and fault[1] == name: r = fault[2]
        v[name] = r
    return ''.join(str(v[o]) for o in outputs)

def fname(f, ckt):                                  # ATALANTA fault-file name
    if f[0] == 'stem': return '%s /%d' % (f[1], f[2])
    gate = next(g for g in ckt[2] if g[0] == f[1])
    return '%s->%s /%d' % (gate[2][f[2]], f[1], f[3])

# ------------------------------------------------------- stage 0 : full list
def full_list(ckt):
    inputs, outputs, gates = ckt
    F = []
    for s in inputs + [g[0] for g in gates]:
        F += [('stem', s, 0), ('stem', s, 1)]
    for name, t, fin in gates:
        for i in range(len(fin)):
            F += [('pin', name, i, 0), ('pin', name, i, 1)]
    return F

# ------------------------------------------------- stage 1 : structural collapse
class UF:
    def __init__(s, items): s.p = {i: i for i in items}
    def find(s, a):
        while s.p[a] != a: s.p[a] = s.p[s.p[a]]; a = s.p[a]
        return a
    def union(s, a, b):
        a, b = s.find(a), s.find(b)
        if a != b: s.p[b] = a

def structural_classes(ckt, F):
    inputs, outputs, gates = ckt
    uf = UF(F)
    fanout = {}
    for name, t, fin in gates:
        for s in fin: fanout[s] = fanout.get(s, 0) + 1
    for name, t, fin in gates:
        for i, s in enumerate(fin):
            if fanout[s] == 1 and s not in outputs:       # one fan-out: stem == pin
                for sa in (0, 1): uf.union(('stem', s, sa), ('pin', name, i, sa))
            # gate rule: input fault equivalent to output fault
            rule = {'AND': (0, 0), 'NAND': (0, 1), 'OR': (1, 1), 'NOR': (1, 0)}.get(t)
            if rule: uf.union(('pin', name, i, rule[0]), ('stem', name, rule[1]))
            if t == 'NOT':
                for sa in (0, 1): uf.union(('pin', name, i, sa), ('stem', name, 1 - sa))
            if t in ('BUFF', 'BUF'):
                for sa in (0, 1): uf.union(('pin', name, i, sa), ('stem', name, sa))
    groups = {}
    for f in F: groups.setdefault(uf.find(f), []).append(f)
    return list(groups.values())

# ------------------------------------------------------------------------ main
def main():
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    bench = sys.argv[1]; base = os.path.splitext(os.path.basename(bench))[0]
    ckt = load_bench(bench); inputs, outputs, gates = ckt
    vecs = list(itertools.product((0, 1), repeat=len(inputs)))
    good = {v: simulate(ckt, v) for v in vecs}

    F0 = full_list(ckt)                                       # stage 0
    classes = structural_classes(ckt, F0)                     # stage 1
    reps = [min(c, key=lambda f: (f[0] != 'stem', str(f))) for c in classes]   # one fault per class
    sig = {}                                                  # response of each fault to all inputs
    for f in reps: sig[f] = ''.join(simulate(ckt, v, f) for v in vecs)
    goodsig = ''.join(good[v] for v in vecs)
    redundant = [f for f in reps if sig[f] == goodsig]        # stage 2
    detectable = [f for f in reps if sig[f] != goodsig]
    seen, collapsed = {}, []                                  # stage 3
    for f in detectable:
        if sig[f] not in seen: seen[sig[f]] = f; collapsed.append(f)

    n0, n1, n2, n3 = len(F0), len(reps), len(detectable), len(collapsed)
    print('=' * 60); print(' FAULT LIST REDUCTION: %s' % bench); print('=' * 60)
    print(' circuit: %d inputs, %d outputs, %d gates' % (len(inputs), len(outputs), len(gates)))
    print(' 0. Full list (all stems + all pins)      : %4d' % n0)
    print(' 1. After structural equivalence collapse : %4d   (-%d)' % (n1, n0 - n1))
    print(' 2. After removing redundant faults       : %4d   (-%d)' % (n2, n1 - n2))
    print(' 3. After functional equivalence collapse : %4d   (-%d)' % (n3, n2 - n3))
    print(' Total reduction: %d -> %d  (%.1f %% fewer faults)' % (n0, n3, 100.0 * (n0 - n3) / n0))
    for f in redundant: print(' redundant fault: ' + fname(f, ckt))

    open(base + '_full.flt', 'w').write('\n'.join(fname(f, ckt) for f in F0) + '\n')
    open(base + '_collapsed.flt', 'w').write('\n'.join(fname(f, ckt) for f in collapsed) + '\n')
    open(base + '_redundant.txt', 'w').write('\n'.join(fname(f, ckt) for f in redundant) + '\n')
    print(' wrote %s_full.flt, %s_collapsed.flt, %s_redundant.txt' % (base, base, base))

    try:                                                       # graph
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        names = ['Full list', 'Structural\ncollapse', 'Redundant\nremoved', 'Functional\ncollapse']
        vals = [n0, n1, n2, n3]
        fig, ax = plt.subplots(figsize=(6.6, 3.7), dpi=200)
        bars = ax.bar(names, vals, color=['#8c8c8c', '#1f5fa8', '#e08e0b', '#2e8b57'], width=.55)
        for b, v in zip(bars, vals): ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * .02, str(v), ha='center', fontweight='bold')
        ax.set_ylabel('Number of faults'); ax.set_ylim(0, max(vals) * 1.15); ax.grid(axis='y', alpha=.3)
        ax.set_title('Fault list reduction: %s' % base, fontsize=10); plt.tight_layout()
        plt.savefig(base + '_fault_list_reduction.png'); print(' wrote %s_fault_list_reduction.png' % base)
    except ImportError:
        print(' (install matplotlib to get the graph: pip install matplotlib)')

if __name__ == '__main__':
    main()
