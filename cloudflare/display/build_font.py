"""Bake antialiased glyphs for the private image beta; no font file is shipped."""
import base64
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import reportlab
FONT_DIR = Path(reportlab.__file__).parent / "fonts"

result = {}
for scale in (2, 3, 4, 5, 6, 7, 8):
    size = {6: 50, 7: 40, 8: 24}.get(scale, scale * 9)
    face = ImageFont.truetype(str(FONT_DIR / ('VeraBd.ttf' if scale in (4, 5, 6, 7) else 'Vera.ttf')), size)
    chars = {}
    for code in range(32, 127):
        char = chr(code)
        advance = round(face.getlength(char))
        box = face.getbbox(char)
        width, height = max(1, box[2] - min(0, box[0])), max(size * 2, scale * 12)
        image = Image.new('L', (width, height))
        ImageDraw.Draw(image).text((-min(0, box[0]), 0), char, font=face, fill=255)
        levels = bytes(round(p * 7 / 255) for p in image.tobytes())
        chars[char] = [width, height, advance, base64.b64encode(levels).decode()]
    result[str(scale)] = chars
Path(__file__).with_name('smooth-font.mjs').write_text(
    'export const smoothFont=' + json.dumps(result, separators=(',', ':')) + ';\n', encoding='utf8')
