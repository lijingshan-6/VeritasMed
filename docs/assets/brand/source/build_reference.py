"""Unified serif identity: two colors, sturdy citation badge and measured alignment."""
import json
from io import BytesIO
from html import escape
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import ImageFont
from build_assets import OUT, HERE, SANS, lettering

ROOT=OUT/'reference'
ROOT.mkdir(exist_ok=True)
serif_file=TTFont(HERE/'dmserifdisplay-DMSerifDisplay-Regular.ttf')
serif_buffer=BytesIO();serif_file.save(serif_buffer)
SERIF=serif_file,ImageFont.truetype(BytesIO(serif_buffer.getvalue()),serif_file['head'].unitsPerEm)
TAG='Medical answers. Evidence you can inspect.'
NAME='VeritasMed'
INK='#17323B';TEAL='#246F80';PAPER='#FAF9F5';DARK='#101C26';WHITE='#F4F5F1';BRIGHT='#8CC5D0'
BADGE_COLORS={False:('#17262F','#1F6F7A','#F4F2EE'),True:('#E9EEF0','#5FB3BF','#0D1117')}
WORD_SIZE=240;WORD_TRACK=-1.5;WORD_GAP=7
TAG_SIZE=42;TAG_TRACK=.30;BASELINE=410;TAG_BASELINE=480;BADGE_PADDING=12


def bounds(text,family,size,track=0):
    ft,pil=family;glyphs=ft.getGlyphSet();cmap=ft.getBestCmap()
    scale=size/ft['head'].unitsPerEm;xs=[];ys=[]
    for i,ch in enumerate(text):
        pen=BoundsPen(glyphs);glyphs[cmap[ord(ch)]].draw(pen)
        if not pen.bounds:continue
        advance=(pil.getlength(text[:i+1])-pil.getlength(ch))*scale+i*track
        x0,y0,x1,y1=pen.bounds
        xs.extend([advance+x0*scale,advance+x1*scale]);ys.extend([y0*scale,y1*scale])
    return min(xs),min(ys),max(xs),max(ys)


def layout(compact=False):
    a=bounds(NAME,SERIF,WORD_SIZE,WORD_TRACK)
    t=bounds(TAG,SANS,TAG_SIZE,TAG_TRACK)
    text_top=BASELINE-a[3]
    text_bottom=BASELINE-a[1] if compact else TAG_BASELINE-t[1]
    badge_size=text_bottom-text_top+2*BADGE_PADDING
    shift=(280 if compact else 360)-(text_top+text_bottom)/2
    name_width=a[2]-a[0]+WORD_GAP
    left=(2160-badge_size-60-name_width)/2
    text_left=left+badge_size+60
    return {'word_bounds':a,'tag_bounds':t,'text_top':text_top+shift,'text_bottom':text_bottom+shift,
            'badge_top':text_top+shift-BADGE_PADDING,'badge_bottom':text_bottom+shift+BADGE_PADDING,
            'badge_size':badge_size,'badge_left':left,'text_left':text_left,
            'word_baseline':BASELINE+shift,'tag_baseline':TAG_BASELINE+shift,'word_width':name_width}


def wordmark(x,baseline,ink,accent):
    ft,pil=SERIF;glyphs=ft.getGlyphSet();cmap=ft.getBestCmap();scale=WORD_SIZE/ft['head'].unitsPerEm
    paths=[]
    for i,ch in enumerate(NAME):
        pen=SVGPathPen(glyphs);glyphs[cmap[ord(ch)]].draw(pen)
        advance=(pil.getlength(NAME[:i+1])-pil.getlength(ch))*scale+i*WORD_TRACK
        if i>=7:advance+=WORD_GAP
        color=accent if i>=7 else ink
        paths.append(f'<path fill="{color}" transform="translate({x+advance:.4f} {baseline:.4f}) scale({scale:.8f} {-scale:.8f})" d="{pen.getCommands()}"/>')
    return '<g aria-label="VeritasMed">'+''.join(paths)+'</g>'


def icon(x,y,size,dark=False,mono=False):
    badge_fill,bracket_fill,v_fill=(INK,WHITE,WHITE) if mono else BADGE_COLORS[dark]
    border=f' stroke="{WHITE}" stroke-opacity=".20" stroke-width=".65"' if dark else ''
    left='M33 20H14V100H33V92H22V28H33Z'
    right='M87 20H106V100H87V92H98V28H87Z'
    v='M30 45H55V49C48 49 46 50 49 56L60 77L82 33L90 36L59 92L36 55C34 51 33 49 30 49Z'
    return (f'<g transform="translate({x:.4f} {y:.4f}) scale({size/120:.8f})">'
            f'<rect width="120" height="120" rx="23" fill="{badge_fill}"{border}/>'
            f'<g fill="{v_fill}"><path'+('' if mono else f' fill="{bracket_fill}"')+f' d="{left}"/><path'+('' if mono else f' fill="{bracket_fill}"')+f' d="{right}"/><path d="{v}"/></g></g>')


def lockup(dark=False,compact=False,mono=False):
    ink=WHITE if dark else INK;accent=BRIGHT if dark else TEAL
    if mono:accent=ink
    m=layout(compact);a=m['word_bounds'];t=m['tag_bounds']
    body=icon(m['badge_left'],m['badge_top'],m['badge_size'],dark,mono)
    body+=wordmark(m['text_left']-a[0],m['word_baseline'],ink,accent)
    if not compact:body+=lettering(TAG,SANS,TAG_SIZE,m['text_left']-t[0],m['tag_baseline'],ink,TAG_TRACK)
    return body


def svg(w,h,body,title,bg=None):
    background=f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">'
            f'<title id="title">{escape(title)}</title><desc id="desc">VeritasMed: a sturdy white citation V in a rounded dark badge; Veritas and Med share the same serif typeface, differentiated only by dark ink and teal.</desc>'
            +background+body+'</svg>\n')


def main():
    for dark in [False,True]:
        tone='dark' if dark else 'light';bg=DARK if dark else PAPER
        assets={
            'logo':svg(2160,720,lockup(dark),'VeritasMed — '+TAG),
            'header':svg(2160,720,lockup(dark),'VeritasMed — '+TAG,bg),
            'compact':svg(2160,560,lockup(dark,True),'VeritasMed'),
            'mark':svg(512,512,icon(16,16,480,dark),'VeritasMed [V] badge'),
            'small':svg(120,120,icon(0,0,120,dark),'VeritasMed [V] small badge'),
            'avatar':svg(512,512,icon(0,0,512,dark),'VeritasMed [V] avatar'),
        }
        for kind,data in assets.items():(ROOT/f'veritasmed-reference-{kind}-{tone}.svg').write_text(data,encoding='utf-8')
    (ROOT/'veritasmed-reference-logo-mono.svg').write_text(svg(2160,720,lockup(mono=True),'VeritasMed — monochrome'),encoding='utf-8')
    (ROOT/'veritasmed-reference-mark-mono.svg').write_text(svg(512,512,icon(16,16,480,mono=True),'VeritasMed [V] monochrome'),encoding='utf-8')
    m=layout()
    metrics={'revision':2,'wordmark':'DM Serif Display Regular, uniform size / scale / weight for all ten letters',
             'wordmark_size':WORD_SIZE,'wordmark_tracking':WORD_TRACK,'word_boundary_extra_space':WORD_GAP,
             'tagline':'Inter 400','tagline_text':TAG,'tagline_size':TAG_SIZE,'tagline_tracking':TAG_TRACK,
             'text_top':m['text_top'],'text_bottom':m['text_bottom'],'badge_top':m['badge_top'],'badge_bottom':m['badge_bottom'],
             'badge_padding_top':BADGE_PADDING,'badge_padding_bottom':BADGE_PADDING,'wordmark_width':m['word_width'],
             'bracket_stroke_in_120_canvas':8,'V_arm_widths_near_terminals':[13,8],
             'light':{'ink_and_tagline':INK,'Med':TEAL,'badge_colors':BADGE_COLORS[False]},'dark':{'ink_and_tagline':WHITE,'Med':BRIGHT,'badge_colors':BADGE_COLORS[True]}}
    (ROOT/'design-metrics.json').write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metrics))


if __name__=='__main__':main()
