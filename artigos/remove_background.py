from PIL import Image

img = Image.open("Confirmation Bias - 2.jpeg")
w, h = img.size  # 2600x808

# Identificar o separador (~x=1270 a x=1330)
x_start, x_end = 1270, 1330

# Cortar os dois painéis e juntar sem separador
left  = img.crop((0, 0, x_start, h))
right = img.crop((x_end, 0, w, h))

# Nova imagem: largura = left + right
new_w = left.width + right.width
joined = Image.new("RGB", (new_w, h))
joined.paste(left, (0, 0))
joined.paste(right, (left.width, 0))

# Redimensionar e guardar
joined_resized = joined.resize((1300, int(1300 * h / new_w)), Image.LANCZOS)
joined_resized.save("Confirmation-Bias-full.png", optimize=True, compress_level=9)
print(f"Guardado: {joined_resized.size}")
