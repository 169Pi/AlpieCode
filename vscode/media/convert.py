from PIL import Image
img = Image.open("icon.jpg")
img.save("icon.png")
print("Converted icon.jpg -> icon.png")
