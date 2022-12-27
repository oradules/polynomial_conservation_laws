#! /usr/bin/env python3

import os, sys, math
import queue
import time
import threading
import multiprocessing
import subprocess


def is_windows():
    return sys.platform == "win32"


def secure_del(fn):
    if fn:
        # don't ever crash the program here
        try:
            os.unlink(fn)
            return True
        except:
            pass


def exec_program(cmd, *, callback):
    q = queue.Queue()

    def poll_thread(q, hnd):
        while True:
            ln = hnd.readline()
            q.put(ln)
            if not ln:
                break

    callback("\n"
        f"# [{multiprocessing.current_process().name}]\n"
        f"# > {' '.join(cmd)}\n")
    tt = time.monotonic()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                errors="backslashreplace", bufsize=0, text=True)
    except FileNotFoundError:
        return

    # create threads
    for hnd in (proc.stdout, proc.stderr):
        t = threading.Thread(target=poll_thread, args=(q, hnd))
        t.daemon = True
        t.start()

    # run down threads
    open_hnd = 2
    while open_hnd > 0:
        ln = q.get()
        if ln:
            if callback:
                callback(ln)
        else:
            open_hnd -= 1

    ret = proc.wait()
    tt = time.monotonic() - tt
    callback(f"\n# (exit {ret})\n")
    callback(f"# (time {tt:.3f})\n")

    return ret


class Outsaver:
    def __init__(self):
        self.s = ""

    def append(self, s):
        self.s += s
        #print(end=s)

    def __call__(self, s):
        self.append(s)

    def get(self):
        return self.s


def run_singular(bm, gen):
    saver = Outsaver()
    timeout_prg = "ixtimeout" if is_windows() else "/usr/bin/timeout"
    singular_prg = None if is_windows() else "/usr/bin/Singular"

    prg_fn = f"_sing{'g' * gen}{bm}.lib"
    with open(prg_fn, "w") as f:
        print(f"""
LIB "allbm{'-gen' * gen}_new2.lib";

int t = timer;
{'gen' * gen}bm{bm}();
"Run-time:", timer-t, "msec";

quit;
""", file=f)
        f.close()

        timeout_sec = 3600
        cmd = [timeout_prg, f"{timeout_sec}s", singular_prg, "--ticks-per-sec", "1000", prg_fn]        
        exec_program(cmd, callback=saver.append)
        
    secure_del(prg_fn)

    with open(os.path.join("out", f"{'g' * gen}bm{bm}.txt"), "w") as f:
        f.write(saver.s)


def runner(args):
    bm, gen = args
    return bm, run_singular(bm, gen)


def run_work_items(items, threads=None, *, nop=False):
    tot = len(items)

    if tot == 0:
        print("Nothing to do")
        return

    if not threads:
        threads = os.cpu_count()

    print(f"Running {tot} work items on {threads} threads\n")

    if nop:
        for i in items:
            bm = i
            print(f"bm{bm}")
        return

    with multiprocessing.Pool(threads) as pool:
        imap_unordered_it = pool.imap_unordered(runner, items)

        for cnt, x in enumerate(imap_unordered_it, 1):
            bm, _ = x
            cstr = f"({cnt:>{len(str(tot))}}/{tot}): "
            cstr += f"bm{bm}"
            print(f"{cstr}")

    print("Done")


def main():
    bms = [2, 6, 28, 30, 38, 40, 46, 69, 72, 80, 82, 85, 86, 92, 99, 102, 103, 108, 150, 156, 159, 198, 199, 200, 205, 243, 252, 257, 270, 282, 283, 292, 314, 315, 335, 357, 359, 360, 361, 362, 363, 364, 365, 405, 430, 431, 447, 475, 483, 530, 539, 552, 553, 609, 614, 629, 647, 651, 667, 676, 679, 680, 687, 688, 707, 710, 742, 745, 747, 748, 755, 758, 780, 781, 782, 783, 793, 795, 815, 827, 854, 868, 870, 875, 880, 882, 886, 887, 894, 905, 906, 916, 922, 932, 934, 940, 951, 957, 968, 987, 1004, 1021, 1024, 1031, 1035, 1037, 1038, 1045, 1053, 1054, ]
    #bms = [159, ]

    gen = False
    pol = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "-g":
            gen = True
        if sys.argv[1] == "-p":
            pol = True
    
    if pol and not gen:
        print(f"Compute polconslaw")
        run_work_items([(i, False) for i in bms])
    elif not pol and gen:
        print(f"Compute genpolconslaw")
        run_work_items([(i, True) for i in bms])
    elif pol and gen:
        print(f"Compute polconslaw and genpolconslaw")
        run_work_items([(i, False) for i in bms] + [(i, True) for i in bms])
    else:
        print(f"Nothing to do.  Use -p, -g, or -b switch")


if __name__ == "__main__":
    main()
