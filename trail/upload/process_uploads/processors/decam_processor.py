"""
Class for processing FITS files processed by DECam Community Pipelines.

These pipelines will bundle entire focal planes into a single file, which can
be successfully processed by the MultiExtensionFits class, but for which we can
create better visualisations.

Note that the focusing and guiding chips are not processed, but are usually
present in Community Pipelines products.
"""

import os

from PIL import Image, ImageOps
import matplotlib.pyplot as plt
import numpy as np


from upload.process_uploads.processors.fits_processors import MultiExtensionFits
from upload.process_uploads.header_standardizer import HeaderStandardizer


__all__ = ["DecamFits", ]


class Detector:
    def __init__(self, row, col,idxtype, label=None):
        self.row = row
        self.col = col
        self.rowType = idxtype
        self.label = label


class DecamFocalPlane:
    row_layout = {
        1:  {"indices": ( (2, 0),  (3, 0),  (4, 0)),
             "names":   ( "S31",   "S30",   "S29"), "rtype": "even"},
        2:  {"indices": ( (1, 1),  (2, 1),  (3, 1),  (4, 1)),
             "names":   ( "S28",   "S27",   "S26",   "S25"), "rtype": "odd"},
        3:  {"indices": ( (1, 2),  (2, 2),  (3, 2),  (4, 2), (5, 2)),
             "names":   ( "S24",   "S23",   "S22",   "S21",  "S20"), "rtype": "even"},
        4:  {"indices": ( (0, 3),  (1, 3),  (2, 3),  (3, 3), (4, 3), (5, 3)),
             "names":   ( "S19",   "S18",   "S17",   "S16",  "S15",  "S14"), "rtype": "odd"},
        5:  {"indices": ( (0, 4),  (1, 4),  (2, 4),  (3, 4), (4, 4), (5, 4)),
             "names":   ( "S13",   "S12",   "S11",   "S10",  "S9",  "S8"), "rtype": "odd"},
        6:  {"indices": ( (0, 5),  (1, 5),  (2, 5),  (3, 5), (4, 5), (5, 5), (6, 5)),
             "names":   ( "S7",    "S6",    "S5",    "S4",   "S3",   "S2",   "S1"), "rtype":"even"},
        7:  {"indices": ( (0, 6),  (1, 6),  (2, 6),  (3, 6), (4, 6), (5, 6), (6, 6)),
             "names":   ( "N7",    "N6",    "N5",    "N4",   "N3",   "N2",   "N1"), "rtype":"even"},
        8:  {"indices": ( (0, 7),  (1, 7),  (2, 7),  (3, 7), (4, 7), (5, 7)),
             "names":   ( "N13",   "N12",   "N11",   "N10",  "N9",  "N8"),"rtype": "odd"},
        9:  {"indices": ( (0, 8),  (1, 8),  (2, 8),  (3, 8), (4, 8), (5, 8)),
             "names":   ( "N19",   "N18",   "N17",   "N16",  "N15",  "N14"),"rtype": "odd"},
        10: {"indices": ( (1, 9),  (2, 9),  (3, 9),  (4, 9), (5, 9)),
             "names":   ( "N24",   "N23",   "N22",   "N21",  "N20"), "rtype": "even"},
        11: {"indices": ((1, 10), (2, 10), (3, 10), (4, 10)),
             "names":   ( "N28",   "N27",   "N26",   "N25"), "rtype": "odd"},
        12: {"indices": ((2, 11), (3, 11), (4, 11)),
             "names":   ( "N31",   "N30",   "N29"), "rtype": "even"},
    }

    detector_index_map = {name:index for row in row_layout.values()
                          for name, index in zip(row["names"], row["indices"])}
    detector_type_map = {name:row["rtype"] for row in row_layout.values()
                         for name in row["names"]}

    nRows = 7
    nCols = 12
    dimX = 4096
    dimY = 2048
    ccd_gap = 208
    row_offset = dimX/2

    def __init__(self, scaling, xdim=None, ydim=None, ccdGap=None, rowOffset=None):
        self.xdim = self.dimX if xdim is None else xdim
        self.ydim = self.dimY if ydim is None else ydim
        self.gap = self.ccd_gap if ccdGap is None else ccdGap
        self.rowOffset = self.row_offset if rowOffset is None else rowOffset
        self.scale = scaling

        self.scaledX = int(self.xdim/scaling)
        self.scaledY = int(self.ydim/scaling)
        self.scaledGap = int(self.gap/scaling)
        self.scaledRowOffset = int(self.scaledX/2)

        self.scaledGappedX = self.scaledX + self.scaledGap
        self.scaledGappedY = self.scaledY + self.scaledGap
        self.scaledGappedOffsetX = self.scaledGappedX*1.5 + self.scaledGap

        self.planeImage = None

        self.detectors = {}
        for row in self.row_layout.values():
            for col, name in zip(row["indices"], row["names"]):
                self.detectors[name] = Detector(row=col[0], col=col[1],
                                                idxtype=row["rtype"], label=name)

    def even_row_indices(self, i, j):
        return int(i*self.scaledGappedX), int(j*self.scaledGappedY)

    def odd_row_indices(self, i, j):
        return (self.scaledRowOffset + i*self.scaledGappedX), j*self.scaledGappedY

    def slice(self, detectorLabel):
        detector = self.detectors[detectorLabel]

        if detector.rowType == "even":
            coords = self.even_row_indices(detector.row, detector.col)
        else:
            coords = self.odd_row_indices(detector.row, detector.col)

        return (slice(coords[0], coords[0]+self.scaledX),
                slice(coords[1], coords[1]+self.scaledY))

    def add_detector(self, hdu):
        name = hdu["DETPOS"]
        row, col = self.detector_index_map[name]
        rtype = self.detector_type_map(name)
        self.detectors[hdu["DETPOS"]] = Detector(row, col, rtype, label=hdu["DETPOS"])
        

    def add_image(self, image, detectorLabel):
        if self.planeImage is None:
            self.planeImage = np.zeros((self.nRows*self.scaledGappedX,
                                        self.nCols*self.scaledGappedY),
                                       dtype=np.uint8)

        start, end = self.slice(detectorLabel)
        self.planeImage[start, end] = image


class DecamFits(MultiExtensionFits):

    name = "DECamCommunityFits"

    def __init__(self, upload):
        super().__init__(upload)

        # Override the default processed exts to filter only science images
        # from all image-like exts, ignoring focus and guider chips.
        self.exts = self._getScienceImages(self.exts)

    @classmethod
    def _getScienceImages(cls, hdulist):
        exts = []
        for hdu in hdulist:
            exttype = hdu.header.get("DETPOS", False)
            if exttype:
                if "G" not in exttype and "F" not in exttype:
                    exts.append(hdu)

        return exts

    @classmethod
    def canProcess(cls, upload, returnHdulist=False):
        canProcess, hdulist = super().canProcess(upload, returnHdulist=True)

        # Data examples I have seen Community Pipeines exclusively utilize the
        # CompImageHDU headers and at any time in history there was at most 1
        # Here, we bet that if we are near 62 CCDs encoded as CompImageHDUs,
        # ignoring guider and focus, we are looking at DECam CP product
        exts = cls._getScienceImages(hdulist)

        if len(exts) > 60 and len(exts) <= 62:
            canProcess = canProcess and True
        else:
            canProcess = canProcess and False

        if returnHdulist:
            return canProcess, hdulist
        return canProcess

    @classmethod
    def normalizeImage(cls, image):
        # astropy equalizer averages 4.3 seconds, the PIL approach can bring
        # that down to cca 0.13. Without normalization the time is 0.04s
        avg, std = image.mean(), image.std()
        image[image>(avg + 0.5*std)] = avg + 0.5*std
        image[image<(avg - 0.5*std)] = avg - 0.5*std
        image = image/image.max()
        image = (image*255).astype(np.uint8)

        image = Image.fromarray(image, "L")
        image = ImageOps.equalize(image, mask=None)

        return image

    def _createFocalPlaneImage(self, focalPlane):
        for ext in self.exts:
            # no matter how painful this is, if we don't, normalize will mutate
            # in place....
            image = ext.data.copy()
            image = self.normalizeImage(image)

            # TODO: test here if the step-vise resizing is faster...
            image = image.resize((focalPlane.scaledY, focalPlane.scaledX),
                                 Image.ANTIALIAS)

            focalPlane.add_image(image, ext.header["DETPOS"])

        return focalPlane

    def storeThumbnails(self, scaling=(4, 10)):

        xdim = self.exts[0].header["NAXIS2"]
        ydim = self.exts[0].header["NAXIS1"]
        largePlane = DecamFocalPlane(scaling=scaling[0], xdim=xdim, ydim=ydim)
        smallPlane = DecamFocalPlane(scaling=scaling[1], xdim=xdim, ydim=ydim)

        # TODO: a note to fix os.path dependency when transitioning to S3
        # and fix saving method from plt to boto3
        smallPath = os.path.join(self.media_root, self._upload.basename+'_plane_small.jpg')
        largePath = os.path.join(self.media_root, self._upload.basename+'_plane_large.jpg')

        smallThumb = self._createFocalPlaneImage(smallPlane)
        plt.imsave(smallPath, smallThumb.planeImage.T, pil_kwargs={"quality":30})
        # due to the size of these images immediately release memory
        del smallThumb

        largeThumb = self._createFocalPlaneImage(largePlane)
        plt.imsave(largePath, largeThumb.planeImage.T, pil_kwargs={"quality":30})
        del largeThumb


