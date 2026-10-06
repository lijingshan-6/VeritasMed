import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path

root=Path(__file__).resolve().parents[1]
assets=json.loads((root/'reference/asset-manifest.json').read_text(encoding='utf-8'))['assets']
for a in assets:
    p=root/'reference'/a['file']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'],p
    assert p.stat().st_size==a['bytes'],p
    if p.suffix=='.svg':
        tree=ET.parse(p);svg=tree.getroot()
        assert float(svg.get('width'))==a['width'] and float(svg.get('height'))==a['height']
        assert all(e.tag.split('}')[-1] not in ['text','image','script','foreignObject'] for e in tree.iter())
        assert not re.search(r'(?:href=|font-family|@font-face)',p.read_text(encoding='utf-8'))
    else:
        im=Image.open(p).convert('RGBA')
        assert im.size==(a['width'],a['height'])
        assert im.getpixel((0,0))[3]==(255 if 'header' in p.name else 0),p

refs=0
for p in [root/'preview.html',root/'preview-reference.html',root.parents[2]/'README.md',root.parents[2]/'README.zh-CN.md']:
    for ref in re.findall(r'(?:src|srcset|href)="([^"]+)"',p.read_text(encoding='utf-8')):
        if ref.startswith(('http','#','mailto:')):continue
        assert (p.parent/ref).is_file(),(p,ref)
        refs+=1

for name in ['dmserifdisplay-OFL.txt','inter-OFL.txt']:
    assert 'SIL OPEN FONT LICENSE' in (root/'source'/name).read_text(encoding='utf-8')
im=Image.open(root/'reference/veritasmed-reference-small-light.png').convert('RGBA').resize((24,24),Image.Resampling.LANCZOS)
pixels={(x,y) for y in range(24) for x in range(24) if max(abs(c-b) for c,b in zip(im.getpixel((x,y))[:3],(23,38,47)))>=45 and im.getpixel((x,y))[3]>=200}
components=0
while pixels:
    components+=1;todo=[pixels.pop()]
    while todo:
        x,y=todo.pop()
        for dx in [-1,0,1]:
            for dy in [-1,0,1]:
                q=(x+dx,y+dy)
                if q in pixels:pixels.remove(q);todo.append(q)
assert components==3,components
ns='{http://www.w3.org/2000/svg}'
svg=ET.parse(root/'reference/veritasmed-reference-logo-light.svg').getroot()
word=next(g for g in svg.findall(ns+'g') if g.get('aria-label')=='VeritasMed')
tag=next(g for g in svg.findall(ns+'g') if g.get('aria-label')=='Medical answers. Evidence you can inspect.')
assert len(word)==10
assert [p.get('fill') for p in word]==['#17323B']*7+['#246F80']*3
assert tag.get('fill')=='#17323B'
scales=[tuple(map(float,re.findall(r'[-+]?\d*\.?\d+',p.get('transform'))))[-2:] for p in word]
assert len(set(scales))==1 and scales[0][0]==-scales[0][1]
def group_bounds(g):
    result=[]
    for p in g:
        pen=BoundsPen(None);parse_path(p.get('d'),pen)
        if pen.bounds is None:continue
        tx,ty,sx,sy=map(float,re.findall(r'[-+]?\d*\.?\d+',p.get('transform')))
        x0,y0,x1,y1=pen.bounds
        result.append((tx+x0*sx,ty+y1*sy,tx+x1*sx,ty+y0*sy))
    return min(p[0] for p in result),min(p[1] for p in result),max(p[2] for p in result),max(p[3] for p in result)
wb=group_bounds(word);tb=group_bounds(tag)
badge=next(g for g in svg.findall(ns+'g') if g.get('transform') and not g.get('aria-label'))
mx,my,ms=map(float,re.findall(r'[-+]?\d*\.?\d+',badge.get('transform')))
assert badge[0].get('fill')=='#17262F'
assert badge[1].get('fill')=='#F4F2EE'
assert [p.get('fill') for p in badge[1]][:2]==['#1F6F7A']*2
top_padding=min(wb[1],tb[1])-my
bottom_padding=my+120*ms-max(wb[3],tb[3])
assert abs(top_padding-12)<.001 and abs(bottom_padding-12)<.001
assert abs(wb[0]-tb[0])<.001
report={'assets_verified':len(assets),'local_references_verified':refs,'svg_self_contained':True,'font_licenses_present':True,'small_symbol_components_at_24px':components,'png_dimensions_backgrounds_and_hashes':True,'wordmark_uniform_scale':True,'wordmark_colors_unchanged':True,'badge_top_padding':round(top_padding,4),'badge_bottom_padding':round(bottom_padding,4),'tagline_left_edge_difference':round(tb[0]-wb[0],4)}
(root/'reference/verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
