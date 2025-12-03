import os
import urllib2
from PIL import Image
from cStringIO import StringIO

def crop23(url):
    image = Image.open(StringIO(urllib2.urlopen(url).read()))
    #Log(image.size or "Nothing here")
    width, height = image.size
    Log("Height-%s, Width-%s", height, width)
    box = (width-(height*2/3),0,width,height)
    Log(box)
    #oooopoasdaojshdf = "asd"
    #cut = image.crop(box)
    return image