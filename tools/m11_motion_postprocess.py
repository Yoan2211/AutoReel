from __future__ import annotations
import json,re,shutil,sys
from pathlib import Path

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def qs(s): return '"' + str(s).replace("\\","\\\\").replace('"','\\"') + '"'

def find_lua(project):
    p=project/"m11_resolve_build"/"autoreel_m11_build.lua"
    if p.is_file(): return p
    c=list(project.glob("m11_resolve_build*/autoreel_m11_build*.lua"))
    if not c: raise FileNotFoundError("Aucun Lua M11")
    c.sort(key=lambda x:x.stat().st_mtime,reverse=True); return c[0]

def busy(timeline):
    for tr in timeline.get("tracks",[]):
        if tr.get("id")=="V2":
            out=[]
            for e in tr.get("events",[]):
                a,b=e.get("timeline_start_us"),e.get("timeline_end_us")
                if isinstance(a,int) and isinstance(b,int): out.append((a,b))
            return out
    return []

def ov(a,b,ints): return any(a<y and x<b for x,y in ints)

def main():
    if len(sys.argv)!=2: raise SystemExit("usage: m11_motion_postprocess.py <project_dir>")
    project=Path(sys.argv[1]).resolve()
    mp=project/"motion_plan.json"; tp=project/"timeline.json"
    if not mp.is_file(): print("[M5B] motion_plan absent"); return
    motion=load(mp); timeline=load(tp); occupied=busy(timeline); fps=60000/1001
    lua=find_lua(project); text=lua.read_text(encoding="utf-8")
    if "-- AutoReel M5B Motion" in text: print("[M5B] déjà injecté"); return
    rows=[]; n=0
    for e in motion.get("events",[]):
        a,b=int(e["cut_start_us"]),int(e["cut_end_us"])
        if ov(a,b,occupied): continue
        p=Path(e["asset_path"])
        if not p.is_file(): continue
        rs,re_=round(a/1e6*fps),round(b/1e6*fps)
        sf=int(e.get("asset_frame_count") or 1); n+=1
        rows += [
            "table.insert(BUILD.tracks.V2, {",
            f"  id = {qs('motion_'+str(n))},",
            f"  physical_path = {qs(str(p.resolve()))},",
            "  source_start_frame = 0,",
            f"  source_end_frame = {sf},",
            f"  record_start_frame = {rs},",
            f"  record_end_frame = {re_},",
            "  media_type = 1,",
            "})",
        ]
    if not rows: print("[M5B] aucune animation à injecter"); return
    snippet="-- AutoReel M5B Motion\nBUILD.tracks.V2 = BUILD.tracks.V2 or {}\n"+"\n".join(rows)+"\ntable.sort(BUILD.tracks.V2,function(a,b)return a.record_start_frame<b.record_start_frame end)\n"
    m=re.search(r"\nlocal function ",text)
    if not m: raise RuntimeError("Point insertion Lua introuvable")
    backup=lua.with_suffix(".lua.before_motion_v4")
    if not backup.exists(): shutil.copy2(lua,backup)
    text=text[:m.start()]+"\n\n"+snippet+text[m.start():]
    lua.write_text(text,encoding="utf-8")
    print(f"[M5B] {n} animation(s) injectée(s) sur V2")

if __name__=="__main__": main()
