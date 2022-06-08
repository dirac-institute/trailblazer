"""
Class for processing FITS files processed by DECam Community Pipelines.

These pipelines will bundle entire focal planes into a single file, which can
be successfully processed by the MultiExtensionFits class, but for which we can
create better visualisations.

Note that the focusing and guiding chips are not processed, but are usually
present in Community Pipelines products.
"""


from PIL import Image, ImageOps
import numpy as np

from .multi_extension_fits import MultiExtensionFits
from upload.models import Thumbnails


__all__ = ["LbtFits", ]
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

    def _createFocalPlaneImage(self, focalPlane):
        for ext in self.exts:
            # no matter how painful this is, if we don't, normalize will mutate
            # in science data in place....
            image = ext.data.copy()
            image = self.normalizeImage(image)

            # TODO: test here if the step-vise resizing is faster...
            image = image.resize((focalPlane.scaledY, focalPlane.scaledX),
                                 Image.ANTIALIAS)

            focalPlane.add_image(image, ext.header["DETPOS"])

        return focalPlane

    def createThumbnails(self, scaling=(4, 10)):

        # NAXIS1  =                 2304 / Image x size                                   
        # NAXIS2  =                 4608 / Image y size
        #center :3,466

        padding = 10
        xdim = 2304*3 + 2*padding
        ydim = 4608 + padding + 2304

        img = np.zeros((xdim, ydim))
        for ccd in self.exts:
            ccddata = self.normalizeImage(ccd.data)
            if '1' in ccd.header['EXTNAME']:
                img[-2304:, -4608:] = ccddata.T
            elif '2' in ccd.header['EXTNAME']:
                img[2304+padding:2*2304+padding, -4608:] = ccddata.T
            elif '3' in ccd.header['EXTNAME']:
                img[:2304, -4608:]= ccddata.T
            else:
                img[1162:1162+4608, :2304] = ccddata

        img = Image.fromarray(img, 'L')
        newY, newX = int(ydim/2), int(xdim/2)
        img = img.resize((newY, newX), Image.ANTIALIAS)
        newY, newX = int(ydim/4), int(xdim/4)
        smallImg = np.asarray(img.resize((newY, newX), Image.ANTIALIAS))
        img = np.asarray(img)
        breakpoint()
        relSmallPath = self.uploadedFile.basename+'_plane_small.jpg'
        relLargePath = self.uploadedFile.basename+'_plane_large.jpg'
        thumb = Thumbnails(large=relLargePath, small=relSmallPath)

        self._storeThumbnail(smallImg.T, savepath=thumb.smallAbsPath)
        self._storeThumbnail(img.T, savepath=thumb.largeAbsPath)

        return thumb
