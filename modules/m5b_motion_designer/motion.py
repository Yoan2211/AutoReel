from __future__ import annotations
import json, math, re, subprocess, unicodedata
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

MEDICAL = (
    "anémie","anemie","fatigue","essoufflement","vertige","vertiges",
    "palpitation","palpitations","pâle","pale","hémoglobine","hemoglobine",
    "sang","oxygène","oxygene","fer","carence","muqueuse","muqueuses",
)
LIST_WORDS = ("premier","première","deuxième","troisième","quatrième","cinquième","signe","signes")
CTA_WORDS = ("abonne","partage","commente","enregistre","suis-moi","lien en bio")
STOP = {"avec","dans","pour","mais","cette","comme","tout","plus","vous","votre","elle","nous","donc","alors","être","avoir","faire","cela","est","les","des","une","que","qui","sur","par","pas","peut"}

@dataclass
class Event:
    id: str
    animation: str
    text: str
    subtitle: str
    cut_start_us: int
    cut_end_us: int
    priority: int
    reason: str
    asset_path: str | None = None
    asset_fps: float = 30.0
    asset_frame_count: int = 0

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def norm(text):
    return unicodedata.normalize("NFC", text.casefold())

def tokens(text):
    return re.findall(r"[\w'-]+", norm(text), re.UNICODE)

def bounds(m):
    s = m.get("source", m)
    c = m.get("cut", m.get("target", {}))
    vals = (
        s.get("start_us", m.get("source_start_us")),
        s.get("end_us", m.get("source_end_us")),
        c.get("start_us", m.get("cut_start_us", m.get("target_start_us"))),
        c.get("end_us", m.get("cut_end_us", m.get("target_end_us"))),
    )
    return None if None in vals else tuple(map(int, vals))

def project(a,b,mappings):
    out=[]
    for m in mappings:
        x=bounds(m)
        if not x: continue
        ss,se,cs,ce=x
        lo,hi=max(a,ss),min(b,se)
        if lo<hi:
            out.append((cs+(lo-ss), cs+(hi-ss)))
    return None if not out else (min(x[0] for x in out), max(x[1] for x in out))

def busy_visuals(visual):
    out=[]
    for r in visual.get("requests",[]):
        if r.get("disposition")=="NONE": continue
        a,b=r.get("cut_start_us"),r.get("cut_end_us")
        if isinstance(a,int) and isinstance(b,int) and a<b: out.append((a,b))
    return out

def overlap(a,b,ivals):
    return any(a<y and x<b for x,y in ivals)

def roles(edit):
    d={}
    for r in edit.get("roles",[]):
        d.setdefault(r.get("passage_id"),set()).add(r.get("role"))
    return d

def section_starts(edit):
    out=set()
    for s in edit.get("sections",[])[1:]:
        ids=s.get("passage_ids") or []
        if ids: out.add(ids[0])
    return out

def keyword(text):
    ts=tokens(text)
    for m in MEDICAL:
        if m in ts: return m.upper()
    cand=[x for x in ts if len(x)>=5 and x not in STOP]
    return (cand[0] if cand else (ts[0] if ts else "À RETENIR")).upper()

def number(text):
    m=re.search(r"\b(\d+(?:[,.]\d+)?\s*%?)\b",text)
    if m: return m.group(1).replace(" ","")
    n=norm(text)
    for word,digit in [("cinq","5"),("quatre","4"),("trois","3"),("deux","2"),("un","1")]:
        if re.search(rf"\b{word}\b",n): return digit
    return None

def select_events(edit,time_map,visual,max_events):
    rmap=roles(edit); sections=section_starts(edit); busy=busy_visuals(visual)
    props=[]
    for p in edit.get("passages",[]):
        text=p.get("text","").strip()
        if not text: continue
        w=project(int(p["source_start_us"]),int(p["source_end_us"]),time_map.get("mappings",[]))
        if not w: continue
        a,b=w
        if b-a<700000: continue
        rr=rmap.get(p["id"],set()); n=norm(text); num=number(text)
        anim=main=sub=reason=None; prio=0
        if num and (re.search(r"\d",text) or any(k in n for k in ("signe","signes","pourcent","femme","personne"))):
            anim,main,sub,prio,reason="NUMBER_COUNT",num,keyword(text).title(),100,"Nombre important"
        elif "HOOK" in rr:
            anim,main,sub,prio,reason="KEYWORD_POP",keyword(text),"À retenir",95,"Hook"
        elif any(k in n for k in MEDICAL):
            anim,main,sub,prio,reason="MEDICAL_CARD",keyword(text),"Information médicale",88,"Concept médical"
        elif any(k in n for k in LIST_WORDS):
            anim,main,sub,prio,reason="LIST_ITEM",keyword(text),"Point clé",82,"Énumération"
        elif any(k in n for k in CTA_WORDS) or "CTA" in rr:
            anim,main,sub,prio,reason="CTA","ENREGISTRE LA VIDÉO","Pour la retrouver plus tard",80,"CTA"
        elif p["id"] in sections:
            anim,main,sub,prio,reason="SECTION_TRANSITION",keyword(text),"Nouveau point",72,"Nouvelle section"
        if not anim: continue
        dur={"NUMBER_COUNT":2000000,"KEYWORD_POP":1500000,"MEDICAL_CARD":1800000,"LIST_ITEM":1600000,"CTA":2000000,"SECTION_TRANSITION":1250000}[anim]
        e=min(b,a+dur)
        if e-a<850000 or overlap(a,e,busy): continue
        props.append(Event("motion_"+p["id"],anim,main[:40],sub[:50],a,e,prio,reason))
    props.sort(key=lambda x:(-x.priority,x.cut_start_us))
    chosen=[]
    for e in props:
        if any(abs(e.cut_start_us-o.cut_start_us)<2200000 for o in chosen): continue
        chosen.append(e)
        if len(chosen)>=max_events: break
    return sorted(chosen,key=lambda x:x.cut_start_us)

def _font(size,bold=False):
    choices=[
        Path(r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
    ]
    for p in choices:
        if p.is_file(): return ImageFont.truetype(str(p),size)
    return ImageFont.load_default()

def _back(t):
    c1,c3=1.70158,2.70158
    return 1+c3*(t-1)**3+c1*(t-1)**2

def _cubic(t): return 1-(1-t)**3
def _alpha(t): return max(0,min(1,t/.12 if t<.12 else ((1-t)/.12 if t>.88 else 1)))

def frame(e,t):
    W,H=1080,1920
    img=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(img); a=int(255*_alpha(t))
    if e.animation=="NUMBER_COUNT":
        s=.72+.28*_back(min(1,t/.35)); w,h=int(760*s),int(380*s); x=(W-w)//2; y=190
        d.rounded_rectangle((x,y,x+w,y+h),46,fill=(9,20,40,int(225*_alpha(t))),outline=(54,123,255,a),width=5)
        d.text((W//2,y+145),e.text,font=_font(int(145*s),True),fill=(255,255,255,a),anchor="mm")
        d.text((W//2,y+295),e.subtitle,font=_font(int(36*s)),fill=(164,196,255,a),anchor="mm")
    elif e.animation=="MEDICAL_CARD":
        p=_cubic(min(1,t/.28)); x=int(-700+p*750); y=300; w,h=690,230
        d.rounded_rectangle((x,y,x+w,y+h),42,fill=(245,249,255,int(238*_alpha(t))))
        d.ellipse((x+28,y+42,x+148,y+162),fill=(39,105,255,a))
        cx,cy=x+88,y+102
        d.rectangle((cx-11,cy-38,cx+11,cy+38),fill=(255,255,255,a)); d.rectangle((cx-38,cy-11,cx+38,cy+11),fill=(255,255,255,a))
        d.text((x+175,y+72),e.text,font=_font(52,True),fill=(12,27,52,a))
        d.text((x+175,y+138),e.subtitle,font=_font(27),fill=(67,89,125,a))
    elif e.animation=="KEYWORD_POP":
        s=.78+.22*_back(min(1,t/.30)); w,h=int(820*s),int(220*s); x=(W-w)//2; y=250
        d.rounded_rectangle((x,y,x+w,y+h),48,fill=(22,83,255,int(230*_alpha(t))))
        d.text((W//2,y+h//2-15),e.text,font=_font(int(60*s),True),fill=(255,255,255,a),anchor="mm")
        d.text((W//2,y+h-32),e.subtitle,font=_font(int(24*s)),fill=(220,232,255,a),anchor="ms")
    elif e.animation=="LIST_ITEM":
        p=_cubic(min(1,t/.25)); x=int(W+80-p*900); y=380; w,h=780,180
        d.rounded_rectangle((x,y,x+w,y+h),38,fill=(10,20,38,int(226*_alpha(t))))
        d.ellipse((x+34,y+35,x+144,y+145),fill=(51,127,255,a)); d.text((x+89,y+91),"✓",font=_font(54,True),fill=(255,255,255,a),anchor="mm")
        d.text((x+175,y+72),e.text,font=_font(46,True),fill=(255,255,255,a),anchor="lm")
        d.text((x+175,y+128),e.subtitle,font=_font(25),fill=(163,185,221,a),anchor="lm")
    elif e.animation=="SECTION_TRANSITION":
        p=_cubic(min(1,t/.22)); w=int(780*p); x=(W-w)//2; y=240
        d.rounded_rectangle((x,y,x+w,y+120),28,fill=(13,28,51,int(220*_alpha(t))))
        if w>250: d.text((W//2,y+60),e.text,font=_font(42,True),fill=(255,255,255,a),anchor="mm")
    elif e.animation=="CTA":
        p=_cubic(min(1,t/.25)); y=int(H+240-p*620); x=120; w,h=840,180
        d.rounded_rectangle((x,y,x+w,y+h),46,fill=(246,250,255,int(244*_alpha(t))),outline=(44,112,255,a),width=4)
        d.text((W//2,y+70),e.text,font=_font(42,True),fill=(13,31,60,a),anchor="mm")
        d.text((W//2,y+125),e.subtitle,font=_font(25),fill=(73,96,135,a),anchor="mm")
    return img

def render(e,render_dir,fps):
    render_dir.mkdir(parents=True,exist_ok=True)
    dur=(e.cut_end_us-e.cut_start_us)/1e6; count=max(1,round(dur*fps))
    out=render_dir/f"{e.id}_{e.animation.lower()}.mov"
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgba","-s","1080x1920","-r",str(fps),"-i","-","-an","-c:v","prores_ks","-profile:v","4444","-pix_fmt","yuva444p10le",str(out)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    assert p.stdin
    for i in range(count):
        p.stdin.write(frame(e,i/max(1,count-1)).tobytes())
    p.stdin.close()
    if p.wait()!=0: raise RuntimeError(f"FFmpeg failed for {e.id}")
    e.asset_path=str(out.resolve()); e.asset_fps=fps; e.asset_frame_count=count

def build_motion_package(transcript_path,edit_plan_path,time_map_path,visual_plan_path,output_plan_path,render_dir,fps=30.0,max_events=8):
    edit=load(edit_plan_path); tm=load(time_map_path); visual=load(visual_plan_path)
    events=select_events(edit,tm,visual,max_events)
    for i,e in enumerate(events,1):
        print(f"[M5B] {i}/{len(events)} {e.animation}: {e.text}",flush=True)
        render(e,Path(render_dir),fps)
    plan={
        "schema_version":"1.0.0","module":{"id":"M5B","version":"1.0.0"},"stage":"motion_designer","time_domain":"CUT",
        "style":{"preset":"CLEAN_MODERN_MEDICAL","canvas":[1080,1920],"alpha":True,"overload_policy":"SPARSE"},
        "events":[e.__dict__ for e in events],
        "summary":{"selected_count":len(events),"rendered_count":sum(bool(e.asset_path) for e in events)}
    }
    Path(output_plan_path).write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return plan
