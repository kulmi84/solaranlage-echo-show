"""Bake the small status line at three times its display resolution."""
import base64
import json
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--font',required=True,help='Path to a locally licensed font file')
args=parser.parse_args()
font = ImageFont.truetype(args.font, 60)
glyphs = {}
for char in set('StandVeraltet: 0123456789.,UTC'):
    advance = round(font.getlength(char))
    image = Image.new('L', (max(1, advance + 4), 84))
    ImageDraw.Draw(image).text((0, 0), char, font=font, fill=255)
    glyphs[char] = [image.width, image.height, advance, base64.b64encode(image.tobytes()).decode()]
(root/'status-font.mjs').write_text('export const statusFont='+json.dumps(glyphs,separators=(',',':'))+';\n')
