#!/usr/bin/env bash
# run_demo.sh - runs the WHOLE project in one go and builds one report.
#
# Usage (from the repo root, Linux / macOS / WSL / Git Bash):
#     bash run_demo.sh
#
# Output: results/demo_report.html (open in a browser) + results/demo_logs/*.log
# Exit code is non-zero if any self-check fails (used by GitHub Actions).
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

command -v iverilog >/dev/null || { echo "iverilog missing: sudo apt install iverilog"; exit 1; }
python3 -c "import matplotlib" 2>/dev/null || { echo "matplotlib missing: sudo apt install python3-matplotlib"; exit 1; }

# Everything generated goes into results/ ; sources are referenced with ../
mkdir -p results/demo_logs
cd results
rm -f demo_logs/*.log demo_logs/*.title

RTL=../rtl ; TB=../tb ; PAT=../atalanta ; PY=../scripts

n=0
step () {                       # step "title" logname command...
  n=$((n+1)); local title="$1" name="$2" log="demo_logs/$2.log"; shift 2
  printf '\n\033[1;36m==== %d. %s ====\033[0m\n' "$n" "$title"
  "$@" 2>&1 | tee "$log"
  echo "$title" > "demo_logs/$name.title"
}

step "Functional check: 200 BCD cases (Verilog)"          01_functional  bash -c "iverilog -o sim.out $RTL/bcd_adder.v $TB/tb_bcd_adder.v && vvp sim.out"
step "Fault list reduction - original circuit (CO2)"      02_reduce      python3 $PY/fault_list_reduction.py $RTL/bcd_adder.bench
step "Fault list reduction - optimized circuit (CO2)"     03_reduce_opt  python3 $PY/fault_list_reduction.py $RTL/bcd_adder_opt.bench
step "Fault simulation - original circuit (CO4)"          04_fsim        python3 $PY/fault_sim.py $RTL/bcd_adder.bench $PAT/bcd_adder.test
step "Fault simulation - optimized circuit (CO4)"         05_fsim_opt    python3 $PY/fault_sim.py $RTL/bcd_adder_opt.bench $PAT/bcd_adder_opt.test
step "Regenerate ATPG testbench from Atalanta patterns"   06_gen_tb      python3 $PY/fault_sim.py $RTL/bcd_adder.bench $PAT/bcd_adder.test --tb atpg_tb.v
step "Apply Atalanta patterns to the Verilog (CO3)"       07_atpg_tb     bash -c "iverilog -o atpg.out $RTL/bcd_adder.v atpg_tb.v && vvp atpg.out"
step "Decoded patterns + HTML report + fault testbench"   08_report      python3 $PY/demo_report.py $RTL/bcd_adder.bench $PAT/bcd_adder.test
step "Fault injection into the Verilog (CO4)"             09_inject      bash -c "iverilog -o fd.out $RTL/bcd_adder.v fault_demo_tb.v && vvp fd.out"

# ---- append every log and the graphs to demo_report.html -------------
python3 - << 'PY'
import glob, html, base64, os
logs = sorted(glob.glob('demo_logs/*.log'))
H = ['<h2>6. Raw output of every run</h2>',
     '<p class="note">Everything below was produced by <code>run_demo.sh</code>.</p>']
for lg in logs:
    title = open(lg[:-4] + '.title').read().strip()
    H.append('<h3>%s</h3><pre style="background:#f4f6fa;border:1px solid #bcc7d6;'
             'padding:8px;overflow:auto;font-size:12px">%s</pre>'
             % (html.escape(title), html.escape(open(lg, errors='replace').read())))
H.append('<h2>7. Fault list reduction graphs</h2>')
for png in ('bcd_adder_fault_list_reduction.png', 'bcd_adder_opt_fault_list_reduction.png'):
    if os.path.exists(png):
        b = base64.b64encode(open(png, 'rb').read()).decode()
        H.append('<p><b>%s</b><br><img style="max-width:100%%" src="data:image/png;base64,%s"></p>' % (png, b))
s = open('demo_report.html', encoding='utf-8').read()
s = s.replace('</body>', '\n'.join(H) + '</body>')
open('demo_report.html', 'w', encoding='utf-8').write(s)
print('\nAppended logs and graphs to demo_report.html')
PY

# ---- self-checks: fail loudly if anything is wrong -------------------
fail=0
check () {                      # check "description" logfile "text that must appear"
  if grep -q "$3" "demo_logs/$2.log"; then echo "  [ok]   $1"
  else echo "  [FAIL] $1"; fail=1; fi
}
printf '\n\033[1;36m==== Self-checks ====\033[0m\n'
check "200 BCD cases pass"                        01_functional "RESULT: PASS"
check "Original: 210 -> 136 faults"               02_reduce     "210 -> 136"
check "Optimized: 204 -> 132 faults"              03_reduce_opt "204 -> 132"
check "Original: 1 redundant fault"               04_fsim       "Redundant faults (undetectable)     : 1"
check "Optimized: 100 % coverage, no redundancy"  05_fsim_opt   "Max attainable fault coverage       : 100.000 %"
check "Atalanta patterns agree with the Verilog"  07_atpg_tb    "RESULT: PASS"

if [ "$fail" -ne 0 ]; then printf '\n\033[1;31mSome checks failed.\033[0m\n'; exit 1; fi
printf '\n\033[1;32mDone. Open results/demo_report.html in your browser.\033[0m\n'
command -v explorer.exe >/dev/null && explorer.exe demo_report.html >/dev/null 2>&1 || true
exit 0
