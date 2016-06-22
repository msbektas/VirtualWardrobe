import noise
import math
from PIL import Image, ImageOps, ImageChops
import time
from Vars import LOG
import inspect
import os

def timeit(func):
    """Times any function. Very useful for debugging slow algorithms."""
    def func_wrapper(*args, **kwargs):
        current_time = time.time()
        ret = func(*args, **kwargs)
        LOG.debug("Time taken to execute function {0}: {1} s".format(str(func.__name__), float(time.time()-current_time)))
        return ret
    return func_wrapper

class TextureCreator(object):
    """docstring for TextureCreator"""
    def __init__(self, samples, printed_texture, size = (2048, 2048), prefix="testing"):
        super(TextureCreator, self).__init__()
        self.samples = samples
        printed_texture = printed_texture
        self.size = size
        self.prefix = prefix
        self.num_per_processing = 1

    def save(self, image):
        """VERY HACKY, ONLY USE TO DEBUG!"""
        LOG.warning("Using hacky save function for lazy debugging.")
        try:
            os.mkdir("image_testing/{0}/".format(self.prefix))
        except Exception as e:
            pass
        frame = inspect.currentframe()
        name = "image"
        for k,v in frame.f_back.f_locals.iteritems():
            if v is image:
                name = k
                break
        image.save("image_testing/{0}/{1}.png".format(self.prefix, name))

    @timeit
    def multiply(self, rgb, mask):
        if rgb.size != mask.size:
            LOG.warning("Image mode or size not matching")
            return None
        new = Image.new(rgb.mode, rgb.size)
        m = mask.convert("L")
        w, h = new.size
        for x in range(0, w):
            for y in range(0, h):
                value = rgb.getpixel((x,y))
                value = tuple(int(i * (m.getpixel((x,y))/255.0)) for i in value)
                new.putpixel((x,y), value)

        return new

    def add(self, img, otherImage):
        if img.mode != otherImage.mode or img.size != otherImage.size:
            LOG.warning("Image mode or size not matching")
            return None
        new = Image.new(img.mode, img.size)
        w, h = new.size
        for x in range(0, w):
            for y in range(0, h):
                value = img.getpixel((x,y))
                otherValue = otherImage.getpixel((x,y))
                newValue = [0]*len(value)
                for i in range(0,len(value)):
                    newValue[i] = value[i] + otherValue[i]

                new.putpixel((x,y), tuple(newValue))

        return new



    def createRandomTexture(self, size, algo=noise.snoise2):
        img = Image.new("L", size)
        h, w = size
        for x in range(0,w):
            for y in range(0,h):
                n = algo(x*0.45, y*0.67)
                r = abs(int(255*n))
                value = (r)
                img.putpixel((int(x),int(y)), value)

        return img

    def tileSmallerTexture(self, smaller, larger):
        s_w, s_h = smaller.size
        tiled = Image.new("RGBA", self.size)
        w, h = tiled.size
        for i in range(0, w, s_w):
            for j in range(0, h, s_h):
                #paste the image at location i, j:
                tiled.paste(smaller, (i, j))

        larger.paste(tiled, (0,0))
        return tiled

    def createTexture(self):
        if len(self.samples) == 0:
            LOG.warning("Not enough samples")
            return Image.new("RGBA", self.size)
        self.texture = Image.new("RGBA", self.size)
        count = 0
        images = []
        for sample in self.samples:
            img = None
            if isinstance(sample, Image.Image):
                img = sample
            else:
                img = Image.open(sample)
            count += 1
            images.append(img)
            if count >= self.num_per_processing:
                count = 0
                self.processSample(images)
                images = []


        return self.texture
    def processSample(self, image):
        pass

class BigTileCreator(TextureCreator):
    """BigTileCreator. Only works for 1 sample!"""
    def processSample(self, images):
        s_image = images[0]
        self.texture = Image.new("RGBA", self.size)
        s_w, s_h = s_image.size
        big_tile = Image.new("RGBA", (s_w*2, s_h*2))
        big_tile.paste(s_image, (0,0))
        big_tile.paste(s_image.transpose(Image.FLIP_LEFT_RIGHT), (s_w,0))
        big_tile.paste(s_image.transpose(Image.FLIP_TOP_BOTTOM), (0,s_h))
        big_tile.paste(s_image.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_LEFT_RIGHT), (s_w,s_h))
        self.tileSmallerTexture(big_tile, self.texture)

        return self.texture

class TilableCreator(TextureCreator):
    """Borrowed from http://paulbourke.net/texture_colour/tiling/"""
    @timeit
    def processSample(self, images):
        s_image = images[0]
        s_w, s_h = s_image.size
        orig_mask = self.createMaskForOrig(s_image.size)
        mask_swapped = self.swapOppositeQuadrants(orig_mask)
        s_swapped = self.swapOppositeQuadrants(s_image)
        tile = Image.new("RGBA", s_image.size)
        tile.paste(s_image, (0,0))
        self.save(s_swapped)
        self.save(mask_swapped)
        tile.paste(s_swapped, (0,0), orig_mask)
        self.save(tile)
        tile.paste(s_image, (0,0), mask_swapped)
        self.save(tile)
        self.tileSmallerTexture(tile, self.texture)

        return self.texture

    def swapOppositeQuadrants(self, image):
        new = Image.new(image.mode, image.size)
        w, h = image.size
        #LOG.debug("Image size {0}".format(image.size))
        for x in range(0, w):
            for y in range(0, h):
                N = w
                new_x = (x+N/2) % N
                new_y = (y+N/2) % N
                value = image.getpixel((new_x, new_y))
                new.putpixel((x,y), value)

        return new

    def createMaskForOrig(self, size):
        mask = Image.new("L", size)
        for x in range(0, size[0]):
            for y in range(0, size[1]):
                N = (size[0])
                value = math.sqrt((x-N/2)**2 + (y-N/2)**2) / (N/2)
                mask.putpixel((x,y), (int(255*value),))
        self.save(mask)
        return mask

class NoiseCreator(TextureCreator):
    """docstring for NoiseCreator"""
    def __init__(self, *args, **kwargs):
        super(NoiseCreator, self).__init__(*args, **kwargs)
        self.num_per_processing = 2

    @timeit
    def processSample(self, images):
        if len(images) != 2:
            LOG.warning("Wrong number of samples. Maybe you have to little?")
            return Image.new("RGBA", self.size)
        sample1 = images[0]
        sample2 = images[1]
        random = Image.open("random.png")
        rand_invert = Image.open("random_invert.png")
        s_w, s_h = sample1.size
        t1 = Image.new("RGBA", self.size)
        self.tileSmallerTexture(sample1, t1)
        t1 = ImageChops.multiply(t1, random.convert("RGBA"))#self.multiply(t1, random)
        t2 = Image.new("RGBA", self.size)
        self.tileSmallerTexture(sample2, t2)
        t2 = ImageChops.multiply(t2, rand_invert.convert("RGBA"))
        self.save(t1)
        self.save(t2)
        self.texture = ImageChops.add(t1, t2)
        return self.texture






if __name__ == "__main__":
    #creator = NoiseCreator(["textures/tests/pink.png", "textures/tests/pink2.png"], None, prefix="grey")
    rand_creator = TextureCreator([], None)
    #img = creator.createTexture()
    img = rand_creator.createRandomTexture(rand_creator.size, noise.pnoise2)
    img.show()
