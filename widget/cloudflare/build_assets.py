"""Build gallery assets from the existing project logo and widget layout."""
import base64
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
assets = ROOT/'assets'
assets.mkdir(exist_ok=True)
logo = Image.open(ROOT.parent.parent/'assets/branding/solaranlage-icon-512.png').convert('RGB')
logo.resize((450,450), Image.Resampling.LANCZOS).save(assets/'icon.png')
preview = Image.new('RGB',(328,552),'#0C151F')
draw = ImageDraw.Draw(preview)
def font(size):
    return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',size)
draw.text((16,16),'Solaranlage',font=font(26),fill='white')
for top,title,value,color in [(64,'PV + BKW','2,30 kW','#FFD166'),(108,'Haus','1,20 kW','#8BCBFF'),(152,'Akku','72 %','#51D3C5')]:
    draw.text((16,top),title,font=font(20),fill='#AFC1D1')
    width=draw.textlength(value,font=font(24))
    draw.text((312-width,top),value,font=font(24),fill=color)
draw.text((16,202),'Beispielansicht',font=font(14),fill='#AFC1D1')
draw.text((16,226),'Stand: 23.10.26, 14:00',font=font(14),fill='#AFC1D1')
draw.text((16,252),'Antippen: Vollbild öffnen',font=font(16),fill='#8BCBFF')
preview.save(assets/'preview.png')
files = {f'/{name}':base64.b64encode((assets/name).read_bytes()).decode('ascii') for name in ['icon.png','preview.png']}
(ROOT/'assets.mjs').write_text('export const publicAssets = '+json.dumps(files)+';\n',encoding='utf-8')
