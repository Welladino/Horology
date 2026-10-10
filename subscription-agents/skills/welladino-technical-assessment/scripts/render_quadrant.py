"""Render an ordinal effort/uncertainty quadrant; unknowns are never plotted."""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def render(data, output):
    image = Image.new('RGB', (1200, 760), 'white')
    draw = ImageDraw.Draw(image)
    font_path = '/System/Library/Fonts/Supplemental/Arial.ttf'
    def font(size):
        try: return ImageFont.truetype(font_path, size)
        except OSError: return ImageFont.load_default(size=size)
    draw.text((75, 25), data.get('title', 'Effort and uncertainty'), fill='#172b4d', font=font(32))
    bounds = (180, 115, 1090, 590)
    draw.rectangle(bounds, fill='#f3f6fa', outline='#526579', width=3)
    draw.line((635,115,635,590), fill='#aab6c4', width=2)
    draw.line((180,352,1090,352), fill='#aab6c4', width=2)
    draw.text((210,135), 'Less effort / more uncertainty', fill='#526579', font=font(22))
    draw.text((665,135), 'More effort / more uncertainty', fill='#526579', font=font(22))
    draw.text((210,545), 'Less effort / less uncertainty', fill='#526579', font=font(22))
    draw.text((665,545), 'More effort / less uncertainty', fill='#526579', font=font(22))
    draw.text((55,300), 'Uncertainty', fill='#172b4d', font=font(22))
    for y,label in [(485,'Low'),(350,'Medium'),(215,'High')]:
        draw.text((190,y-30),label,fill='#526579',font=font(18))
    for x,label in [(335,'Low'),(635,'Medium'),(935,'High')]:
        draw.text((x-25,605),label,fill='#526579',font=font(20))
    draw.text((565,640), 'Implementation effort', fill='#172b4d', font=font(24))
    ratings={'low':0,'medium':1,'high':2}
    unknown=[]
    for option in data.get('options', []):
        effort=option.get('effort','unknown').lower()
        uncertainty=option.get('uncertainty','unknown').lower()
        if effort not in (*ratings,'unknown') or uncertainty not in (*ratings,'unknown'):
            raise ValueError('Ratings must be Low, Medium, High, or Unknown')
        name=option['name']
        if effort=='unknown' or uncertainty=='unknown':
            unknown.append(name); continue
        x=335+300*ratings[effort]; y=485-135*ratings[uncertainty]
        colour='#175da8' if option.get('recommended',False) else '#986126'
        draw.ellipse((x-10,y-10,x+10,y+10),fill=colour)
        label=name+(' (recommended)' if option.get('recommended',False) else '')
        draw.text((x-100,y+14),label,fill=colour,font=font(19))
    note='Unknown: '+', '.join(unknown) if unknown else ('Unrated template: no assessment yet.' if not data.get('options') else 'Ordinal ratings; consult the written reasons. This is not an approval score.')
    draw.text((75,705),note,fill='#526579',font=font(20))
    image.save(output)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args=parser.parse_args()
    render(json.loads(args.source.read_text()),args.output)
