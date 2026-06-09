from PIL import Image

img = Image.open("Confirmation-Bias-full.png").convert("RGB")
w, h = img.size

# Separador proporcional: original 1270-1330px em 2600px → ~635-665px em 1300px
x_start, x_end = 635, 665

left  = img.crop((0, 0, x_start, h))
right = img.crop((x_end, 0, w, h))

new_w = left.width + right.width
joined = Image.new("RGB", (new_w, h))
joined.paste(left, (0, 0))
joined.paste(right, (left.width, 0))

joined.save("Confirmation-Bias-full2.png", optimize=True, compress_level=9)
print(f"Guardado: {joined.size}")
