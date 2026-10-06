"""Rebuild VeritasMed's outlined SVG identity from the bundled OFL fonts.

Requires Python, fontTools and Pillow. Raster exports: node render_assets.cjs.
The originals are retained unchanged. No fonts are required by exported SVGs.
"""
from io import BytesIO
from pathlib import Path
from html import escape

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from PIL import ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
PAPER, INK, PETROL, MUTED = '#FAF8F3', '#252D30', '#315F6B', '#59666A'
DARK, WHITE, MIST = '#172126', '#F4F2EA', '#9FC3CA'
TAGLINE = 'Medical answers, traced to sources.'


def font(name, axes):
    path = next(HERE.glob(name + '-*.ttf'))
    ft = instantiateVariableFont(TTFont(path), axes, inplace=False)
    buf = BytesIO()
    ft.save(buf)
    return ft, ImageFont.truetype(BytesIO(buf.getvalue()), ft['head'].unitsPerEm)


SERIF = font('newsreader', {'opsz': 60, 'wght': 500})
SANS = font('inter', {'opsz': 14, 'wght': 400})


def lettering(value, family, size, x, baseline, color, tracking=0):
    ft, pil = family
    glyphs, cmap = ft.getGlyphSet(), ft.getBestCmap()
    upm = ft['head'].unitsPerEm
    scale = size / upm
    paths = []
    for i, ch in enumerate(value):
        name = cmap[ord(ch)]
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(pen)
        # Prefix measurement retains the kerning applied to the current pair.
        advance = (pil.getlength(value[:i+1]) - pil.getlength(ch)) * scale + i * tracking
        if pen.getCommands():
            paths.append(f'<path transform="translate({x+advance:.4f} {baseline}) scale({scale:.8f} {-scale:.8f})" d="{pen.getCommands()}"/>')
    return f'<g fill="{color}" aria-label="{escape(value)}">' + ''.join(paths) + '</g>'


def folios(x, y, size, color):
    # Two original folios; the open seam is real transparency, not a white stroke.
    left = 'M8 12 Q8 8 12 10 L39 22 Q43 24 43 29 L43 87 L13 74 Q8 72 8 66 Z'
    right = 'M53 29 Q53 24 57 22 L84 10 Q88 8 88 12 L88 66 Q88 72 83 74 L53 87 Z'
    return (f'<g fill="{color}" transform="translate({x} {y}) scale({size/96:.8f})">'
            f'<path d="{left}"/><path d="{right}"/></g>')


def svg(width, height, body, title, background=None):
    bg = f'<rect width="{width}" height="{height}" fill="{background}"/>' if background else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
            f'<title id="title">{escape(title)}</title><desc id="desc">VeritasMed: two open literature folios forming an abstract V, with a serif wordmark.</desc>'
            + bg + body + '</svg>\n')


def lockup(fg=INK, accent=PETROL, sub=MUTED):
    return (folios(204, 103, 162, accent)
            + lettering('VeritasMed', SERIF, 153, 410, 220, fg, -0.4)
            + lettering(TAGLINE, SANS, 29, 417, 274, sub, 0.05))


def write(name, data):
    (OUT / name).write_text(data, encoding='utf-8')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    write('veritasmed-logo-light.svg', svg(1440, 360, lockup(), 'VeritasMed — Medical answers, traced to sources.'))
    write('veritasmed-logo-dark.svg', svg(1440, 360, lockup(WHITE, MIST, '#BBC5C7'), 'VeritasMed — Medical answers, traced to sources.'))
    write('veritasmed-logo-mono.svg', svg(1440, 360, lockup(INK, INK, INK), 'VeritasMed — monochrome identity'))
    write('veritasmed-header-light.svg', svg(1440, 360, lockup(), 'VeritasMed — Medical answers, traced to sources.', PAPER))
    write('veritasmed-header-dark.svg', svg(1440, 360, lockup(WHITE, MIST, '#BBC5C7'), 'VeritasMed — Medical answers, traced to sources.', DARK))
    compact = folios(129, 47, 138, PETROL) + lettering('VeritasMed', SERIF, 135, 304, 158, INK, -0.4)
    write('veritasmed-wordmark.svg', svg(1160, 240, compact, 'VeritasMed'))
    compact_dark = folios(129, 47, 138, MIST) + lettering('VeritasMed', SERIF, 135, 304, 158, WHITE, -0.4)
    write('veritasmed-wordmark-dark.svg', svg(1160, 240, compact_dark, 'VeritasMed'))
    for name, color in [('light', PETROL), ('dark', MIST), ('mono', INK)]:
        write(f'veritasmed-mark-{name}.svg', svg(512, 512, folios(76, 76, 360, color), 'VeritasMed symbol'))
    write('veritasmed-mark-small.svg', svg(96, 96, folios(0, 0, 96, PETROL), 'VeritasMed small symbol'))
    write('veritasmed-mark-small-dark.svg', svg(96, 96, folios(0, 0, 96, MIST), 'VeritasMed small symbol'))
    write('veritasmed-avatar.svg', svg(512, 512, folios(76, 76, 360, PETROL), 'VeritasMed avatar', PAPER))
    social = (lockup() + lettering('Ask. Inspect. Follow the source.', SANS, 24, 417, 353, MUTED))
    write('veritasmed-social.svg', svg(1440, 720, f'<g transform="translate(0 120)">{social}</g>', 'VeritasMed — medical literature and inspectable answers', PAPER))
    print('Built 14 outlined SVG assets; wordmark Newsreader 500 / opsz 60, tagline Inter 400 / opsz 14.')


if __name__ == '__main__':
    main()
