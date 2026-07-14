# -*- coding: utf-8 -*-
"""Mockups: world-class Skills module — command center, matrix heatmap, gap analysis, employee profile."""
import os, subprocess, math
OUT=os.path.dirname(os.path.abspath(__file__)); W=1320
CSS=open(os.path.join(OUT,'_css.txt')).read()
CSS+="""
.tile{display:inline-block;vertical-align:top;width:150px;background:#fff;border:1px solid #e2e8f0;border-radius:11px;padding:11px;margin:0 9px 10px 0;cursor:pointer}
.tile .l{font-size:11px;color:#64748b}.tile .v{font-size:20px;font-weight:bold;margin-top:2px}.tile .b{height:4px;border-radius:3px;margin-top:5px}
.card{display:inline-block;vertical-align:top;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:14px;margin:0 9px 12px 0;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.ct{font-weight:bold;color:#0f2b5b;margin-bottom:10px;font-size:14px}
.idea{background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:11px 14px;font-size:12.5px;color:#9a3412;margin:10px 9px 0 0}
.lvl{display:inline-block;width:13px;height:13px;border-radius:3px;margin:1px}
.mtx td,.mtx th{border:1px solid #e2e8f0;padding:5px 7px;font-size:12px;text-align:center}
.mtx th{background:#0f2b5b;color:#fff}.mtx td.emp{text-align:right;background:#f8fafc;font-weight:bold;color:#334155}
.bar{display:inline-block;height:13px;border-radius:5px;vertical-align:middle}
.barbg2{display:inline-block;width:160px;height:13px;background:#eef2f7;border-radius:5px;vertical-align:middle}
.tag{display:inline-block;border-radius:20px;padding:1px 9px;font-size:11px;color:#fff}
.g{background:#21b07b}.r{background:#e25563}.o{background:#f59e0b}.b{background:#3a7afe}.p{background:#8b5cf6}
"""
def shell(t,c,b):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='b'>CARE • Employees</span><span class='c'>{c}</span><span class='u'>◐ Skills</span></div>
<div class='wrap'><div class='h1'>{t}</div>{b}</div></body></html>"""
def tiles(d): return "".join(f"<div class='tile'><div class='l'>{l}</div><div class='v' style='color:{c}'>{v}</div><div class='b' style='background:{c}'></div></div>" for l,v,c in d)
def hb(label,val,mx,color,w=160):
    return f"<div style='margin:5px 0;font-size:12px'><span style='display:inline-block;width:130px'>{label}</span><span class='barbg2' style='width:{w}px'><span class='bar' style='width:{int(val/mx*w)}px;background:{color}'></span></span> <b>{val}</b></div>"
def dots(n,total=5):
    s=""
    for i in range(total):
        c="#0f2b5b" if i<n else "#e2e8f0"
        s+=f"<span class='lvl' style='background:{c}'></span>"
    return s
S=[]

# 1) Skills Command Center
kp=[("مهارات الموظفين","9,110","#0f2b5b"),("المهارات بالكتالوج","108","#3a7afe"),("أنواع المهارات","9","#017e84"),
("موظفون لديهم مهارات","2,025","#21b07b"),("متوسط/موظف","4.5","#8b5cf6"),("شهادات سارية","312","#0ea5e9"),
("شهادات تنتهي ≤60ي","27","#f59e0b"),("فجوات مهارية حرجة","14","#e25563")]
heat=""
for emp,lvls in [("سونام",[5,3,4,2]),("راج",[4,5,3,4]),("بير",[3,2,5,3]),("علي",[5,4,4,5])]:
    cells="".join(f"<td>{dots(l)}</td>" for l in lvls)
    heat+=f"<tr><td class='emp'>{emp}</td>{cells}</tr>"
b=f"""<div class='sub'>مركز قيادة المهارات — رؤية عميقة لمهارات القوى العاملة · كل بطاقة قابلة للضغط</div>
{tiles(kp)}
<div class='card' style='width:330px'><div class='ct'>المهارات حسب النوع</div>
{hb('Language',4629,4629,'#3a7afe')}{hb('Personnel',2362,4629,'#8b5cf6')}{hb('Technical',2110,4629,'#017e84')}{hb('Communication',5,4629,'#f59e0b')}</div>
<div class='card' style='width:360px'><div class='ct'>أكثر المهارات شيوعاً</div>
{hb('Appearance',1578,1578,'#0f2b5b')}{hb('English',1131,1578,'#3a7afe')}{hb('Cleaning',1117,1578,'#21b07b')}{hb('Nepali',1051,1578,'#8b5cf6')}{hb('Bangladeshi',942,1578,'#f59e0b')}</div>
<div class='card' style='width:340px'><div class='ct'>إتقان اللغات</div>
{hb('عربي',1320,2100,'#21b07b')}{hb('إنجليزي',1131,2100,'#3a7afe')}{hb('نيبالي',1051,2100,'#8b5cf6')}{hb('بنغالي',942,2100,'#f59e0b')}</div>
<div class='card' style='width:1290px'><div class='ct'>خريطة حرارية للمهارات (عيّنة) · مستوى الإتقان 1–5</div>
<table class='mtx'><tr><th>الموظف</th><th>Cleaning</th><th>English</th><th>Safety</th><th>Driving</th></tr>{heat}</table></div>
<div class='idea' style='width:1290px'>💡 الأفكار: تقييم دوري للمهارات (Assessment) · شهادات بتواريخ انتهاء وتنبيهات · مصفوفة المهارات Heatmap · تحليل الفجوة لكل وظيفة · ربط المهارة بالتدريب · توصية تلقائية بالمرشحين حسب المهارة · مهارات حرجة لكل مشروع · بروفايل رادار لكل موظف.</div>"""
S.append(("skills_dashboard","مركز قيادة المهارات",shell("مركز قيادة المهارات","Employees › Skills › Command Center",b)))

# 2) Skills Matrix (full heatmap)
cols=["Cleaning","English","Arabic","Safety/HSE","Driving","Hospitality","Security","Teamwork"]
emps=[("سونام · نظافة",[5,3,4,4,1,2,1,4]),("راج · أمن",[2,4,3,5,3,1,5,4]),("بير · ضيافة",[3,5,4,3,1,5,2,5]),
      ("علي · سائق",[1,3,4,4,5,1,3,3]),("كومار · نظافة",[5,2,3,4,1,2,1,4]),("حسن · أمن",[2,3,3,5,4,1,5,3])]
th="".join(f"<th>{c}</th>" for c in cols)
tr=""
for name,lvls in emps:
    cells="".join(f"<td>{dots(l)}</td>" for l in lvls)
    tr+=f"<tr><td class='emp'>{name}</td>{cells}</tr>"
b=f"""<div class='sub'>مصفوفة المهارات — كل موظف × كل مهارة مع مستوى الإتقان (1–5) · فلاتر حسب القسم/الوظيفة/المشروع</div>
<div class='card' style='width:1290px'>
<table class='mtx'><tr><th>الموظف / القسم</th>{th}</tr>{tr}</table>
<div style='margin-top:8px;font-size:12px'>الدليل: {dots(5)} متقدّم · {dots(3)} متوسط · {dots(1)} مبتدئ</div></div>
<div class='card' style='width:640px'><div class='ct'>توزيع مستويات الإتقان</div>
{hb('مستوى 5 (خبير)',640,2400,'#0f2b5b')}{hb('مستوى 4',1120,2400,'#21b07b')}{hb('مستوى 3',2400,2400,'#3a7afe')}{hb('مستوى 2',1800,2400,'#f59e0b')}{hb('مستوى 1',900,2400,'#e25563')}</div>
<div class='card' style='width:620px'><div class='ct'>تغطية المهارات حسب القسم</div>
{hb('نظافة',88,100,'#21b07b')}{hb('أمن',74,100,'#3a7afe')}{hb('ضيافة',81,100,'#8b5cf6')}{hb('سائقون',69,100,'#f59e0b')}</div>"""
S.append(("skills_matrix","مصفوفة المهارات (Heatmap)",shell("مصفوفة المهارات","Employees › Skills › Skills Matrix",b)))

# 3) Skill Gap Analysis
rows=[("حارس أمن","Safety/HSE · Security · English","78%","المطلوب 4 / المتوسط 3.1","31 ناقص","r"),
      ("عامل نظافة","Cleaning · Safety · Teamwork","92%","المطلوب 4 / المتوسط 4.2","8 ناقص","g"),
      ("سائق","Driving · Safety · English","65%","المطلوب 4 / المتوسط 2.8","44 ناقص","r"),
      ("ضيافة","Hospitality · English · Appearance","83%","المطلوب 4 / المتوسط 3.6","17 ناقص","o")]
tr="".join(f"<tr><td>{r[0]}</td><td class='small'>{r[1]}</td><td class='center'><span class='barbg2' style='width:120px'><span class='bar' style='width:{int(int(r[2][:-1])/100*120)}px;background:{'#21b07b' if r[5]=='g' else ('#f59e0b' if r[5]=='o' else '#e25563')}'></span></span> {r[2]}</td><td class='center'>{r[3]}</td><td class='center'><span class='badge {r[5]}'>{r[4]}</span></td></tr>" for r in rows)
b=f"""<div class='sub'>تحليل فجوة المهارات — المطلوب لكل وظيفة مقابل الواقع · يكشف من ينقصه ماذا ويغذّي خطة التدريب</div>
{tiles([('فجوات حرجة','14','#e25563'),('وظائف تحت المستوى','3','#f59e0b'),('موظفون يحتاجون تدريباً','317','#8b5cf6'),('متوسط التغطية','80%','#21b07b')])}
<div class='card' style='width:1000px'><div class='ct'>الفجوة حسب الوظيفة</div>
<table><tr><th>الوظيفة</th><th>المهارات المطلوبة</th><th class='center'>التغطية</th><th class='center'>المستوى</th><th class='center'>الفجوة</th></tr>{tr}</table></div>
<div class='card' style='width:280px'><div class='ct'>إجراءات مقترحة</div>
<div class='kv'>📚 خطة تدريب للسائقين (English/Safety)</div><div class='kv'>🎯 ترشيح 31 حارساً لدورة HSE</div><div class='kv'>🔁 إعادة توزيع ذوي المهارة العالية</div>
<div class='idea'>💡 ربط الفجوة بأكاديمية التدريب وإنشاء دورة بضغطة واحدة.</div></div>"""
S.append(("skills_gap","تحليل فجوة المهارات",shell("تحليل الفجوة","Employees › Skills › Gap Analysis",b)))

# 4) Employee Skill Profile (radar)
def radar(vals,labels,cx=150,cy=150,R=110):
    n=len(vals); pts=[]; axis=""
    for i,v in enumerate(vals):
        ang=-math.pi/2+2*math.pi*i/n
        x=cx+R*v/5*math.cos(ang); y=cy+R*v/5*math.sin(ang); pts.append(f"{x:.0f},{y:.0f}")
        ax=cx+R*math.cos(ang); ay=cy+R*math.sin(ang)
        axis+=f"<line x1='{cx}' y1='{cy}' x2='{ax:.0f}' y2='{ay:.0f}' stroke='#e2e8f0'/>"
        lx=cx+(R+18)*math.cos(ang); ly=cy+(R+18)*math.sin(ang)
        axis+=f"<text x='{lx:.0f}' y='{ly:.0f}' font-size='10' text-anchor='middle' fill='#475569'>{labels[i]}</text>"
    rings="".join(f"<circle cx='{cx}' cy='{cy}' r='{R*k/5:.0f}' fill='none' stroke='#eef2f7'/>" for k in range(1,6))
    return f"<svg width='320' height='300'>{rings}{axis}<polygon points='{' '.join(pts)}' fill='rgba(15,43,91,.18)' stroke='#0f2b5b' stroke-width='2'/></svg>"
b=f"""<div class='sub'>بروفايل مهارات الموظف — رادار + الشهادات + سجل التقييم</div>
<div class='card' style='width:360px'><div class='ct'>سونام باهادور · عامل نظافة</div>{radar([5,3,4,4,2,4],['Cleaning','English','Safety','Teamwork','Driving','Hospitality'])}</div>
<div class='card' style='width:470px'><div class='ct'>الشهادات والتراخيص</div>
<table><tr><th>الشهادة</th><th class='center'>الإصدار</th><th class='center'>الانتهاء</th><th class='center'>الحالة</th></tr>
<tr><td>HSE Basic</td><td class='center'>2024-03</td><td class='center'>2026-03</td><td class='center'><span class='tag g'>سارية</span></td></tr>
<tr><td>Food Handling</td><td class='center'>2023-08</td><td class='center'>2025-08</td><td class='center'><span class='tag o'>تنتهي قريباً</span></td></tr>
<tr><td>First Aid</td><td class='center'>2022-01</td><td class='center'>2024-01</td><td class='center'><span class='tag r'>منتهية</span></td></tr></table>
<div class='idea'>💡 تنبيه تلقائي بتجديد الشهادات + منع التكليف بمهمة تتطلّب شهادة منتهية.</div></div>
<div class='card' style='width:420px'><div class='ct'>سجل التقييم</div>
<div class='kv'><b>آخر تقييم</b> 2026-05 · المقيّم: مشرف الموقع</div><div class='kv'><b>التقدّم</b> Cleaning 4→5 · Safety 3→4</div><div class='kv'><b>التوصية</b> جاهز للترقية لمشرف</div>
<div class='kv'><b>التأييدات (Endorsements)</b> 6 من زملاء/مدراء</div></div>"""
S.append(("skills_profile","بروفايل مهارات الموظف",shell("بروفايل المهارات","Employees › Skills › Employee Profile",b)))

for fn,title,html in S:
    hp=os.path.join(OUT,fn+".html");pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(html)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width","--width",str(W),"--quality","92",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp);print("rendered",fn)
