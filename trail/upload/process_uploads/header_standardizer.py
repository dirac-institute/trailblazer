"""
Class that facilitates FITS header standardization to keys required by models.
"""

from abc import ABC, abstractmethod
import warnings

import numpy as np

from astropy.io.fits import PrimaryHDU, CompImageHDU
from astropy.wcs import WCS, FITSFixedWarning
import astropy.units as u

__all__ = ["HeaderStandardizer", ]


class HeaderStandardizer(ABC):
    """Supports standardization of various headers.

    Standardization consists of:
    * converting WCS information contained in each image-like header such as
      PrimaryHDU, CompImageHDu etc. (i.e. each header for which it is infered
      by its Astropy type will contain image under its `data` attribute; as
      opposed to BinTableHDU etc.) into a standard set of keys as defined by
      the database models.
    * converting a set of header keywords into metadata keys as defined by the
      database models. The mandatory data consists of observatory location,
      instrument description and time of observation while the remaining
      metadata may vary.


    Parameters
    ----------
    header : `object`
         The header, Astropy HDU and its derivatives.
    \**kwargs : `dict`
       Additional keyword arguments

    Keyword arguments
    -----------------
    filename : `str`
        Name of the file from which the HDU was read from, sometimes can encode
        additional metadata.
    """

    standardizers = dict()
    """All registered header standardizers."""

    @abstractmethod
    def __init__(self, header, **kwargs):
        self.header = header
        self._kwargs = kwargs

    def __init_subclass__(cls, **kwargs):
        name = getattr(cls, "name", False)
        if name and name is not None:
            super().__init_subclass__(**kwargs)
            HeaderStandardizer.standardizers[cls.name] = cls

    @staticmethod
    def _computeStandardizedWcs(header, dimX, dimY):
        """Given an Header containing WCS data and the dimensions of an image
        calculates the values of world coordinates at image corner and image
        center and projects them to a unit sphere in Cartesian coordinate
        system.

        Parameters
        ----------
        header : `object`
            The header, Astropy HDU and its derivatives.
        dimX : `int`
            Image dimension in x-axis.
        dimY : `int`
            Image dimension in y-axis.

        Returns
        -------
        standardizedWcs : `dict`
            Calculated coorinate values, a dict with wcs_radius,
            wcs_center_[x, y, z] and wcs_corner_[x, y, z]

        Notes
        -----
        The center point is the center of the image as determined its
        dimensions directly or via header keywords NAXIS1 and NAXIS2, and the
        corner is taken to be the (0,0)-th pixel.
        World coords. at the points are to unit sphere, in Cartesian system,
        and the distance between them is calculated.
        """
        standardizedWcs = {}
        centerX, centerY = int(dimX/2), int(dimY/2)

        # TODO: When eventually logging is added to processing, redirect these
        # warnings to the logs instead of silencing
        # NOTE: test if a header doesn't actually have a valid WCS
        # what is the error raised
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FITSFixedWarning)
            wcs = WCS(header)

        centerSkyCoord = wcs.pixel_to_world(centerX, centerY)
        centerRa = centerSkyCoord.ra.to(u.deg)
        centerDec = centerSkyCoord.dec.to(u.deg)

        cornerSkyCoord = wcs.pixel_to_world(0, 0)
        cornerRa = cornerSkyCoord.ra.to(u.deg)
        cornerDec = cornerSkyCoord.dec.to(u.deg)

        unitSphereCenter = np.array([
            np.cos(centerDec) * np.cos(centerRa),
            np.cos(centerDec) * np.sin(centerRa),
            np.sin(centerDec)
        ])

        unitSphereCorner = np.array([
            np.cos(cornerDec) * np.cos(cornerRa),
            np.cos(cornerDec) * np.sin(cornerRa),
            np.sin(cornerDec)
        ])

        unitRadius = np.linalg.norm(unitSphereCenter-unitSphereCorner)
        standardizedWcs["wcs_radius"] = unitRadius

        standardizedWcs["wcs_center_x"] = unitSphereCenter[0]
        standardizedWcs["wcs_center_y"] = unitSphereCenter[1]
        standardizedWcs["wcs_center_z"] = unitSphereCenter[2]

        standardizedWcs["wcs_corner_x"] = unitSphereCorner[0]
        standardizedWcs["wcs_corner_y"] = unitSphereCorner[1]
        standardizedWcs["wcs_corner_z"] = unitSphereCorner[2]

        return standardizedWcs

    # wow, do not flip these two decorators around...
    @classmethod
    @abstractmethod
    def canStandardize(self, header, **kwargs):
        """Returns `True` when the standardizer knows how to handle given
        upload.

        Parameters
        ----------
        header : `object`
             The header, Astropy HDU and its derivatives.
        \**kwargs : `dict`
            Additional keyword arguments

        Keyword arguments
        -----------------
        filename : `str`
            Name of the file from which the HDU was read from, sometimes can encode
            additional metadata.

        Returns
        -------
        canProcess : `bool`
            `True` when the processor knows how to handle uploaded file and
            `False` otherwise
        """
        raise NotImplemented()

    @classmethod
    def getStandardizer(cls, header, **kwargs):
        """Get the standardizer class that can handle given header.

        Parameters
        ----------
        header : `object`
             The header, Astropy HDU and its derivatives.
        \**kwargs : `dict`
            Additional keyword arguments

        Keyword arguments
        -----------------
        filename : `str`
            Name of the file from which the HDU was read from, sometimes can encode
            additional metadata.

        Returns
        -------
        standardizerCls : `cls`
            Standardizer class that can process the given upload.`

        Raises
        ------
        ValueError
            None of the registered processors can process the  upload.
        """
        for standardizerCls in cls.standardizers.values():
            if standardizerCls.canStandardize(header, **kwargs):
                return standardizerCls

        raise ValueError("None of the known standardizers can handle this header.\n "
                         f"Known standardizers: {list(cls.standardizers.keys())}")

    @classmethod
    def fromHeader(cls, header, **kwargs):
        """Get the standardizer instance from a given header.

        Parameters
        ----------
        header : `object`
             The header, Astropy HDU and its derivatives.
        \**kwargs : `dict`
            Additional keyword arguments

        Keyword arguments
        -----------------
        filename : `str`
            Name of the file from which the HDU was read from, sometimes can encode
            additional metadata.

        Returns
        -------
        standardizerCls : `cls`
            Standardizer class that can process the given upload.`

        Raises
        ------
        ValueError
            None of the registered processors can process the  upload.
        """
        # TODO: get some error handling here
        standardizerCls = cls.getStandardizer(header, **kwargs)
        return standardizerCls(header, **kwargs)

    @abstractmethod
    def standardizeMetadata(self):
        """Normalizes FITS header information of the primary header unit and
        returns a dictionary with standardized, as understood by trailblazer,
        keys.

        Returns
        -------
        standardizedKeys : `dict`
          A dictionary with standardized header keys and values.
        """
        raise NotImplemented()

    def standardizeWcs(self, hdu=None):
        """Standardize WCS data a given header. 
        Standardized keys are the Cartesian components of world coordinates of
        central and corner points on the image as projected onto a unit sphere
        and the distance between them.

        Parameters
        ----------
        hdu : `obhect` or `None`, optional
            An Astropy image-like HDU unit. Useful when dealing with
            mutli-extension fits files where metadata is in the PrimaryHDU but
            the WCS and image data are stored in the extensions.

        Returns
        -------
        standardizedWCS : `dict`
            A dictionary with standardized WCS keys and values.

        Raises
        ------
        ValueError
            Header contains no image dimension keys (NAXIS1, NAXIS2) but an
            additional HDU was not provided.
        ValueError
            An additional image-like header was provided but contains no image
            data.
        TypeError
            Provided additional HDU is not image-like HDU.
        """
        dimX = self.header.get("NAXIS1", False)
        dimY = self.header.get("NAXIS2", False)
        if not dimX or not dimY:
            if hdu is None:
                raise ValueError("Header contains no image dimension keys "
                                 "(NAXIS1, NAXIS2) but an additional HDU was "
                                 "not provided")

            if not (isinstance(hdu, PrimaryHDU) or isinstance(hdu, CompImageHDU)):
                raise TypeError(f"Expected image-like HDU, got {type(hdu)} instead.")

            if hdu.data is None:
                raise ValueError("Given image-type HDU contains no image to take"
                                 "image dimensions from.")

            dimX, dimY = hdu.data.shape
            header = hdu.header
        else:
            header = self.header

        return self._computeStandardizedWcs(header, dimX, dimY)

    def standardize(self, hdu=None):
        """Convenience function that standardizes the WCS and metadata and
        returns a dictionary with standardized keys.

        Parameters
        ----------
        hdu : `obhect` or `None`, optional
            An Astropy image-like HDU unit. Useful when dealing with
            mutli-extension fits files where metadata is in the PrimaryHDU but
            the WCS and image data are stored in the extensions.

        Returns
        -------
        standardizedKeys : `dict`
            A dictionary with standardized WCS and metadata keys and values.
        """
        # TODO: get some error handling here
        standardizedKeys = {"metadata" : self.standardizeMetadata()}
        standardizedKeys.update({"wcs" :self.standardizeWcs(hdu=hdu)})
        return standardizedKeys
