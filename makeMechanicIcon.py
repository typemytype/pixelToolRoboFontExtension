import os
resourcesFolder = os.path.join(os.getcwd(), 'source', 'resources')
imgPath = os.path.join(resourcesFolder, 'pixelToolbarIcon.png')

size(512, 512)

im = ImageObject()
with im:
    scale(29.01)
    image(imgPath, (-1.29, -1.31))

steps = 10
w = h = width() / (steps-1)
r = w * 0.5

for i in range(steps):
    for j in range(steps):
        x = i * w
        y = j * h        
        X, Y = x + w / 2, y + h / 2
        color = imagePixelColor(im, (X, Y))[-1]
        if color < 0.5:
            continue
        linearGradient((x, y+h), (x+w, y), [(0.3,), (0,)], [0, 1])
        rect(X - r, Y - r, r*2, r*2)

imgPathDest = os.path.join(os.getcwd(), 'PixelToolMechanicIcon.png')
saveImage(imgPathDest)
