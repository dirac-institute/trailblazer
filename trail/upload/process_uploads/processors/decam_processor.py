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

from .multi_extension_fits import MultiExtensionFits
from upload.models import Thumbnails


__all__ = ["DecamFits", ]


row_layout = {
    1:  {"indices": ( (2, 0),  (3, 0),  (4, 0)),
         "names":   ( "S29",   "S30",   "S31"), "rtype": "even"},
    2:  {"indices": ( (1, 1),  (2, 1),  (3, 1),  (4, 1)),
         "names":   ( "S25",   "S26",   "S27",   "S28"), "rtype": "odd"},
    3:  {"indices": ( (1, 2),  (2, 2),  (3, 2),  (4, 2), (5, 2)),
         "names":   ( "S20",   "S21",   "S22",   "S23",  "S24"), "rtype": "even"},
    4:  {"indices": ( (0, 3),  (1, 3),  (2, 3),  (3, 3), (4, 3), (5, 3)),
         "names":   ( "S14",   "S15",   "S16",   "S17",  "S18",  "S19"), "rtype": "odd"},
    5:  {"indices": ( (0, 4),  (1, 4),  (2, 4),  (3, 4), (4, 4), (5, 4)),
         "names":   ( "S8",   "S9",   "S10",   "S11",  "S12",  "S13"), "rtype": "odd"},
    6:  {"indices": ( (0, 5),  (1, 5),  (2, 5),  (3, 5), (4, 5), (5, 5), (6, 5)),
         "names":   ( "S1",    "S2",    "S3",    "S4",   "S5",   "S6",   "S7"), "rtype":"even"},
    7:  {"indices": ( (0, 6),  (1, 6),  (2, 6),  (3, 6), (4, 6), (5, 6), (6, 6)),
         "names":   ( "N1",    "N2",    "N3",    "N4",   "N5",   "N6",   "N7"), "rtype":"even"},
    8:  {"indices": ( (0, 7),  (1, 7),  (2, 7),  (3, 7), (4, 7), (5, 7)),
         "names":   ( "N8",   "N9",   "N10",   "N11",  "N12",  "N13"),"rtype": "odd"},
    9:  {"indices": ( (0, 8),  (1, 8),  (2, 8),  (3, 8), (4, 8), (5, 8)),
         "names":   ( "N14",   "N15",   "N16",   "N17",  "N18",  "N19"),"rtype": "odd"},
    10: {"indices": ( (1, 9),  (2, 9),  (3, 9),  (4, 9), (5, 9)),
         "names":   ( "N20",   "N21",   "N22",   "N23",  "N24"), "rtype": "even"},
    11: {"indices": ((1, 10), (2, 10), (3, 10), (4, 10)),
         "names":   ( "N25",   "N26",   "N27",   "N28"), "rtype": "odd"},
    12: {"indices": ((2, 11), (3, 11), (4, 11)),
         "names":   ( "N29",   "N30",   "N31"), "rtype": "even"},
}
"""A row-based layour of the DECam focal plane science detectors."""


class Detector:
    """A single DECam science CCD detector.""""""

    Attributes
    ----------
    scaling : `float`
        Detector size scaling factor. Detector's scaled size is the detector's
        physical size divided by the scaling factor.
    idx : `tuple`, optional
        Detector zero-based index (row, col), as counted from the center of a
        detector.
    label : `str`, optional
        Detector label, for example S1, S3 etc.
    xdim : `int`, optional
        Detector's physical width, in pixels. Defaults to 4096.
    ydim : `int`, optional
        Detector's physical height, in pixels. Defaults to 2048
    """
    index_detector_map = {name:index for row in row_layout.values()
                          for name, index in zip(row["names"], row["indices"])}
    """Map between detector index and detector label."""

    detector_index_map = {name:index for row in row_layout.values()
                          for name, index in zip(row["names"], row["indices"])}
    """Map between detector labels and their positional indices."""

    detector_type_map = {name:row["rtype"] for row in row_layout.values()
                         for name in row["names"]}
    """Map between detector labels and their row type."""

    dimX = 4096
    """Default, assumed, width, in pixels, of a detector."""

    dimY = 2048
    """Default, assumed, height, in pixels, of a detector."""

    def __init__(self, scaling, idx=None, label=None, xdim=None, ydim=None):
        if idx is not None:
            self.row, self.col = idx
            self.label = self.index_detector_map[idx]
            self.rowType = self.detector_type_map[self.label]
        elif label is not None:
            self.row, self.col = self.detector_index_map[label]
            self.label = label
            self.rowType = self.detector_type_map[label]

        self.scale = scaling
        self.setDimensions(xdim, ydim)

    def setDimensions(self, xdim=None, ydim=None):
        """Updates the detector dimensions using the default or provided values
        and recalculates relavant detector's scaled dimensions.

        Parameters
        ----------
        xdim : `int`
            New detector width.
        ydim : `int`
            New detector height.
        """
        self.xdim = xdim if xdim is not None else self.dimX
        self.ydim = ydim if ydim is not None else self.dimY

        self.scaledX = int(self.xdim/self.scale)
        self.scaledY = int(self.ydim/self.scale)


class DecamFocalPlane:
    """Represents the science only CCDs of the DECam focal plane.
    All CCDs are assumed to have the same size and the same scaling factor.

    Parameters
    ----------
    scaling : `float`
        Scaling factor for which the focal plane size in pixels will be reduced
        by in order to be displayed.
    detectorSize : `tuple`, optional
        Physical detector size in pixels as a tuple (width, height). Defaults
        to (4096, 2048) as set in `Detector`.
    ccdGap : `int`, optional
        Physical size of the gap between detectors, in pixels. Defaults to 208.
    rowOffset : `int`, optional
        Physical offset, in pixels, between 'even' and 'odd' rows.
    """
    detector_labels = [name for row in row_layout.values() for name in row["names"]]
    """A list of all detector labels."""

    nRows = 7
    """Number of detector rows in the focal plane."""

    nCols = 12
    """Number of columns in the focal plane."""

    ccd_gap = 208
    """Default, assumed, gap size in pixels, between two detectors."""

    row_offset = Detector.dimX/2
    """Default, assumed, offset between even and odd rows."""

    def __init__(self, scaling, detectorSize=None, ccdGap=None, rowOffset=None):
        self.scale = scaling
        self.gap = self.ccd_gap if ccdGap is None else ccdGap
        self.rowOffset = self.row_offset if rowOffset is None else rowOffset
        self.__initAssumedDetectorDimensions(detectorSize)

        self.detectors = {}
        for label in self.detector_labels:
            self.detectors[label] = Detector(scaling, label=label)

        self.planeImage = None

    def __initAssumedDetectorDimensions(self, detectorSize=None):
        """In general there is no reason to assume all detectors have the same
        sizes, gaps or offsets. But for DECam they do and this lets us perform
        an easy and quick generation of in-focal-plane-image-array coordinate
        calculations.

        Unfortunately it also requires pre-calculating and storing a lot of
        not-very-clear quantities.
        """
        if detectorSize is None:
            xdim, ydim = Detector.dimX, Detector.dimY
        else:
            xdim, ydim = detectorSize

        self.xdim = xdim
        self.ydim = ydim

        self.scaledX = int(self.xdim/self.scale)
        self.scaledY = int(self.ydim/self.scale)

        self.scaledGap = int(self.gap/self.scale)
        self.scaledRowOffset = int(self.scaledX/2)

        self.scaledGappedX = self.scaledX + self.scaledGap
        self.scaledGappedY = self.scaledY + self.scaledGap
        self.scaledGappedOffsetX = self.scaledGappedX*1.5 + self.scaledGap

    def _even_row_coords(self, i, j):
        return (i*self.scaledGappedX), int(j*self.scaledGappedY)

    def _odd_row_coords(self, i, j):
        return (self.scaledRowOffset + i*self.scaledGappedX), j*self.scaledGappedY

    def get_coords(self, detectorLabel):
        """Get start and end coordinates of the scaled detector.

        Parameters
        ----------
        detectorLabel : `str`
            Label of the detector in the focal plane.

        Returns
        -------
        xCoordinates : `tuple`
            Tuple of start and end coordinates in the x axis.
        yCoordinates : `tuple`
            Tuple of start and end coordinates in the y axis.
        """
        detector = self.detectors[detectorLabel]
        if detector.rowType == "even":
            coords = self._even_row_coords(detector.row, detector.col)
        elif detector.rowType == "odd":
            coords = self._odd_row_coords(detector.row, detector.col)
        else:
            raise ValueError("Unrecognized row type. Expected 'odd' or 'even' "
                             "got {detector.rowType} instead.")

        return (coords[0], coords[0]+self.scaledX), (coords[1], coords[1]+self.scaledY)

    def get_slice(self, detectorLabel):
        """Get array slice that covers the area of the detector.

        Parameters
        ----------
        detectorLabel : `str`
            Label of the detector in the focal plane.

        Returns
        -------
        xSlice : `slice`
            An edge-to-edge slice of the detector, i.e. [start:end], in x axis.
        ySlice : `tuple`
            An edge-to-edge slice of the detector, i.e. [start:end], in y axis.
        """
        coords = self.get_coords(detectorLabel)
        return slice(*coords[0]), slice(*coords[1])

    def add_image(self, image, detectorLabel):
        """Will place the given image at the location of the given detector
        label.

        Parameters
        ----------
        image : `np.array`
            A 2D array representing the image that will be placed at the
            location of the detector
        detectorLabel : `str`
            The label of the detector.

        Note
        ----
        Depending on the scaling factor used, materializing the full focal
        plane can require a lot of memory. The plane image will not be
        materialized until the firt image is placed in it.
        """
        if self.planeImage is None:
            self.planeImage = np.zeros((self.nRows*self.scaledGappedX,
                                        self.nCols*self.scaledGappedY),
                                       dtype=np.uint8)

        start, end = self.get_slice(detectorLabel)
        self.planeImage[start, end] = image


class DecamFits(MultiExtensionFits):

    name = "DECamCommunityFits"
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
            exttype = hdu.header.get("DETPOS", False)
            if exttype:
                if "G" not in exttype and "F" not in exttype:
                    exts.append(hdu)

        return exts

    @classmethod
    def canProcess(cls, uploadedFile, returnHdulist=False):
        canProcess, hdulist = super().canProcess(uploadedFile, returnHdulist=True)

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
            # in science data in place....
            image = ext.data.copy()
            image = self.normalizeImage(image)

            # TODO: test here if the step-vise resizing is faster...
            image = image.resize((focalPlane.scaledY, focalPlane.scaledX),
                                 Image.ANTIALIAS)

            focalPlane.add_image(image, ext.header["DETPOS"])

        return focalPlane

    def createThumbnails(self, scaling=(4, 10)):

        xdim = self.exts[0].header["NAXIS2"]
        ydim = self.exts[0].header["NAXIS1"]
        largePlane = DecamFocalPlane(scaling[0], (xdim, ydim))
        smallPlane = DecamFocalPlane(scaling[1], (xdim, ydim))

        # TODO: a note to fix os.path dependency when transitioning to S3
        # and fix saving method from plt to boto3
        smallPath = os.path.join(self.media_root, self.uploadedFile.basename+'_plane_small.jpg')
        largePath = os.path.join(self.media_root, self.uploadedFile.basename+'_plane_large.jpg')

        smallThumb = self._createFocalPlaneImage(smallPlane)
        self._storeThumbnail(smallThumb.planeImage.T, savepath=smallPath)
        # due to potential size of these images immediately release memory
        del smallThumb

        largeThumb = self._createFocalPlaneImage(largePlane)
        self._storeThumbnail(largeThumb.planeImage.T, savepath=largePath)
        del largeThumb

        return Thumbnails(large=largePath, small=smallPath)
