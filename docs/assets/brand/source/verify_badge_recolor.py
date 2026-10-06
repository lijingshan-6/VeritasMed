"""Prove that the requested badge recolor leaves geometry and all other pixels intact."""
import copy
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

root=Path(__file__).resolve().parents[1]
old=root/'reference-v2';new=root/'reference';ns='{http://www.w3.org/2000/svg}'
palettes={'light':['#17262F','#1F6F7A','#F4F2EE'],'dark':['#E9EEF0','#5FB3BF','#0D1117']}

def badge(svg):
    return next(g for g in svg.findall(ns+'g') if g.get('transform') and not g.get('aria-label'))

def mask_icon_fills(svg):
    tree=copy.deepcopy(svg)
    for node in badge(tree).iter():node.attrib.pop('fill',None)
    return ET.tostring(tree)

changed=0;unchanged=[]
for p in sorted(new.glob('*.svg')):
    before=old/p.name
    if 'mono' in p.name:
        for name in [p.name,p.with_suffix('.png').name]:
            assert (old/name).read_bytes()==(new/name).read_bytes(),name
            unchanged.append(name)
        continue
    a=ET.parse(before).getroot();b=ET.parse(p).getroot()
    assert mask_icon_fills(a)==mask_icon_fills(b),p.name
    tone='dark' if '-dark' in p.name else 'light';expected=palettes[tone];g=badge(b)
    assert g[0].get('fill')==expected[0]
    assert [path.get('fill') for path in g[1]][:2]==[expected[1]]*2
    assert g[1].get('fill')==expected[2] and g[1][2].get('fill') is None
    # Every pixel outside the badge rectangle plus its antialias margin must match.
    im_a=Image.open(before.with_suffix('.png')).convert('RGBA')
    im_b=Image.open(p.with_suffix('.png')).convert('RGBA')
    assert im_a.size==im_b.size
    x,y,s=map(float,re.findall(r'[-+]?\d*\.?\d+',g.get('transform')))
    scale=im_b.width/float(b.get('width'));margin=4
    box=(math.floor(x*scale)-margin,math.floor(y*scale)-margin,
         math.ceil((x+120*s)*scale)+margin,math.ceil((y+120*s)*scale)+margin)
    diff=ImageChops.difference(im_a,im_b);ImageDraw.Draw(diff).rectangle(box,fill=(0,0,0,0))
    assert diff.convert('RGB').getbbox() is None and diff.getchannel('A').getbbox() is None,p.name
    changed+=1

report={'recolored_svg_assets':changed,'palette':palettes,'geometry_and_non_icon_svg_content_unchanged':True,
        'all_non_icon_png_pixels_unchanged':True,'monochrome_assets_unchanged':unchanged}
(new/'badge-color-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
