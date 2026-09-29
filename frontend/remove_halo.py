from PIL import Image

def remove_green_halo(image_path, output_path):
    img = Image.open(image_path).convert("RGBA")
    datas = img.getdata()
    
    newData = []
    bg_color = (8, 11, 53, 255) # Login background
    
    for r, g, b, a in datas:
        # Detect pure green background
        if g > 200 and r < 100 and b < 100:
            newData.append((255, 255, 255, 0)) # fully transparent
        # Detect green halo/edges (where green dominates over red and blue)
        elif g > r + 30 and g > b + 30:
            # We replace the greenish pixels with the dark blue background color,
            # keeping some of the original alpha/intensity if we wanted, but making it dark blue is safest
            newData.append((8, 11, 53, a))
        else:
            newData.append((r, g, b, a))
            
    img.putdata(newData)
    img.save(output_path, "PNG")

remove_green_halo(r'C:\Users\Camco\.gemini\antigravity\brain\fd5733c5-3a6a-42c5-ad39-6feec8112cce\zorro_greenscreen_1790614952239.jpg', r'C:\Users\Camco\email-riwifront\Email-Automation\frontend\src\assets\zorro_full.png')
