"""
Class for processing FITS files processed by Large Binocular Telescope.

These pipelines will bundle entire focal planes into a single file, which can
be successfully processed by the MultiExtensionFits class, but for which we can
create better visualisations.
"""


from PIL import Image
import numpy as np

from .multi_extension_fits import MultiExtensionFits
from upload.models import Thumbnails


__all__ = ["LbtFits", ]


class LbtConstants:
    """Defines the dimensions of individual CCDs, the focal
    plane and the placement of CCDs in the focal plane.
    """

    fill = 10
    """Padding between CCDs on the final image."""

    ccdx = 2304
    """Width, in pixels, of ccd."""

    ccdy = 4608
    """Height, in pixles, of a ccd."""

    focx = 3*ccdx + 2*fill
    """Width, in pixels, of the focal plane."""

    focy = ccdy + fill + ccdx
    """Height, in pixels, of the focal plane."""


class LbtFits(MultiExtensionFits):

    name = "LbtFits"
    priority = 2

    def __init__(self, uploadInfo, uploadedFile):
        super().__init__(uploadInfo, uploadedFile)
        # Override the default processed exts to filter only science images
        # from all image-like exts, ignoring focus and guider chips.
        self.exts = self._getScienceImages(self.exts)

    @classmethod
    def _getScienceImages(cls, hdulist):
        exts = []
        for hdu in hdulist:
            exttype = hdu.header.get("XTENSION", False)
            if exttype.strip() == 'IMAGE':
                exts.append(hdu)

        return exts

    @classmethod
    def canProcess(cls, uploadedFile, returnHdulist=False):
        canProcess, hdulist = super().canProcess(uploadedFile, returnHdulist=True)
        origin = hdulist[0].header.get("ORIGIN", False)
        if origin and "LBT Observatory" == origin:
            return True
        return False

    def createThumbnails(self, scaling=(4, 10), dim=None):
        if dim is None:
            dim = LbtConstants()

        img = np.zeros((dim.focx, dim.focy))

        for ccd in self.exts:
            ccddata = self.normalizeImage(ccd.data)
            if '1' in ccd.header['EXTNAME']:
                img[-dim.ccdx:, -dim.ccdy:] = np.fliplr(ccddata.T)
            elif '2' in ccd.header['EXTNAME']:
                startx = dim.ccdx + dim.fill
                endx = 2*dim.ccdx + dim.fill
                img[startx:endx, -dim.ccdy:] = np.fliplr(ccddata.T)
            elif '3' in ccd.header['EXTNAME']:
                img[:dim.ccdx, -dim.ccdy:] = np.fliplr(ccddata.T)
            else:
                # top row we start half-way through first ccd
                startx, endx = int(dim.ccdx/2)+dim.fill, int(dim.focx/2) + dim.ccdx
                img[startx:endx, :dim.ccdx] = np.flip(ccddata)

        img = (img - img.min()) * 255/(img.max() - img.min())
        img = Image.fromarray(img.astype(np.uint8), 'L')

        newY, newX = int(dim.focy/scaling[0]), int(dim.focx/scaling[0])
        img = img.resize((newY, newX), Image.ANTIALIAS)
        newY, newX = int(dim.focy/scaling[1]), int(dim.focx/scaling[1])
        smallImg = np.asarray(img.resize((newY, newX), Image.ANTIALIAS))
        img = np.asarray(img)

        relSmallPath = self.uploadedFile.basename+'_plane_small.jpg'
        relLargePath = self.uploadedFile.basename+'_plane_large.jpg'
        thumb = Thumbnails(large=relLargePath, small=relSmallPath)

        self._storeThumbnail(smallImg.T, savepath=thumb.smallAbsPath)
        self._storeThumbnail(img.T, savepath=thumb.largeAbsPath)

        return thumb
