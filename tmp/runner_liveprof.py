import sys, os, time, threading, pstats, cProfile, runpy, pathlib, faulthandler

pathlib.Path("reports").mkdir(exist_ok=True)
faulthandler.enable(open("reports\\faulthandler.log","w"))

prof = cProfile.Profile()
dump_path = "reports\\prof_live.pstats"
txt_path  = "reports\\prof_live.txt"

def dumper():
    while True:
        try:
            prof.dump_stats(dump_path)
            with open(txt_path, "w", encoding="utf-8") as f:
                ps = pstats.Stats(dump_path, stream=f).sort_stats("cumtime")
                ps.print_stats(40)
        except Exception as e:
            open("reports\\prof_err.txt","a",encoding="utf-8").write(repr(e)+"\n")
        time.sleep(30)

t = threading.Thread(target=dumper, daemon=True); t.start()

# 実行引数を設定（スモーク特徴で実行中の前提）
sys.argv = ["model_lightgbm_v2.py",
            "--config","configs/tdnet_2014.yaml",
            "--label","y_2x",
            "--folds-config","reports/cv_t5_y_2x_v2.json",
            "--use-features"]

print("[MARK] runner start"); sys.stdout.flush()
prof.enable()
try:
    runpy.run_path("scripts/model_lightgbm_v2.py", run_name="__main__")
finally:
    prof.disable()
    prof.dump_stats(dump_path)
    with open(txt_path, "w", encoding="utf-8") as f:
        pstats.Stats(dump_path, stream=f).sort_stats("cumtime").print_stats(80)
    print("[MARK] runner end"); sys.stdout.flush()
