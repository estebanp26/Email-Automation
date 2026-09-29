from PIL import Image
import sys

def remove_green(image_path, output_path):
    img = Image.open(image_path).convert("RGBA")
    datas = img.getdata()
    
    newData = []
    for item in datas:
        # Green screen is very green, so r < 100, g > 200, b < 100 roughly
        if item[0] < 120 and item[1] > 200 and item[2] < 120:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
            
    img.putdata(newData)
    img.save(output_path, "PNG")

remove_green(r'C:\Users\Camco\.gemini\antigravity\brain\fd5733c5-3a6a-42c5-ad39-6feec8112cce\zorro_greenscreen_1790614952239.jpg', r'C:\Users\Camco\email-riwifront\Email-Automation\frontend\src\assets\zorro_full.png')
