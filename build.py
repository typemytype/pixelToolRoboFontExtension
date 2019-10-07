import os, shutil
from mojo.extensions import ExtensionBundle

basePath = os.path.dirname(__file__)
sourcePath = os.path.join(basePath, 'source')
libPath = os.path.join(sourcePath, 'code')
htmlPath = os.path.join(sourcePath, 'docs')
resourcesPath = os.path.join(sourcePath, 'resources')
licensePath = os.path.join(basePath, 'LICENSE')
pycOnly = False
extensionFile = 'PixelTool.roboFontExt'
extensionPath = os.path.join(basePath, extensionFile)

B = ExtensionBundle()
B.name = "PixelTool"
B.developer = 'TypeMyType'
B.developerURL = 'http://www.typemytype.com'
B.icon = os.path.join(basePath, 'PixelToolMechanicIcon.png')
B.version = '1.5'
B.launchAtStartUp = True
B.mainScript = 'PixelTool.py'
B.html = True
B.requiresVersionMajor = '3'
B.requiresVersionMinor = '2'
B.addToMenu = [
    {
        'path' : 'generateImageFont.py',
        'preferredName': 'Export Font to Bitmaps',
        'shortKey' : '',
    },
]

with open(licensePath) as license:
    B.license = license.read()

# copy README docs to extension docs
# shutil.copyfile(os.path.join(basePath, 'README.md'), os.path.join(htmlPath, 'index.md'))
# shutil.copyfile(os.path.join(basePath, 'PixelTool.png'), os.path.join(htmlPath, 'PixelTool.png'))

print('building extension...', end=' ')
B.save(extensionPath, libPath=libPath, htmlPath=htmlPath, resourcesPath=resourcesPath, pycOnly=pycOnly)
print('done!')

print()
print(B.validationErrors())
