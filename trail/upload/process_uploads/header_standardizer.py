"""
Class that facilitates FITS header standardization to keys required by models.
"""

from abc import ABC, abstractmethod
import warnings
import logging

import numpy as np
from astropy.io.fits import PrimaryHDU, CompImageHDU
from astropy.io import fits
from astropy.wcs import WCS
import astropy.units as u
from astroquery.astrometry_net import AstrometryNet
from trail.settings import ASTROMETRY_KEY

import upload.models as models

__all__ = ["HeaderStandardizer", ]


logger = logging.getLogger(__name__)

ASTRONET_CLIENT = AstrometryNet()

if ASTROMETRY_KEY:
    ASTRONET_CLIENT.api_key = ASTROMETRY_KEY


class HeaderStandardizer(ABC):
    """Supports standardization of various headers.

    Standardization consists of:
        * standardizing WCS data by projecting WCS onto a unit sphere
        * standardizing PrimaryHDU data to find time and location of observer,
          and select optional values such as filter, science program etc.

    Parameters
    ----------
    header : `object`
         The header, Astropy HDU and its derivatives.
    **kwargs : `dict`
       Additional keyword arguments

    Keyword arguments
    -----------------
    filename : `str`
        Name of the file from which the HDU was read from, sometimes can encode
        additional metadata.

    Notes
    -----
    Standardizers are intended to operate on primary headers, but not all
    primary headers contain all of the required metadata. Standardizers must be
    instantiated with the header containing at least the time and location of
    the observer and can be dynamically given a different HDU from which to
    standardize WCS.
    """

    standardizers = dict()
    """All registered header standardizers."""

    name = None
    """Standardizer's name. Only named standardizers will be registered."""

    priority = 0
    """Priority. Standardizers with high priority are prefered over
    standardizers with low priority when processing header metadata.
    """

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
        The center point is assumed to be at the (dimX/2, dimY/2) pixel
        location. Corner is taken to be the (0,0)-th pixel.
        """
        standardizedWcs = {}
        centerX, centerY = int(dimX/2), int(dimY/2)

        # TODO: test if a header doesn't actually have a valid WCS
        # what is the error raised?
        with warnings.catch_warnings(record=True) as warns:
            wcs = WCS(header)
            if warns:
                for w in warns:
                    logger.warning(w.message)

        centerSkyCoord = wcs.pixel_to_world(centerX, centerY)
        centerRa = centerSkyCoord.ra.to(u.rad)
        centerDec = centerSkyCoord.dec.to(u.rad)

        cornerSkyCoord = wcs.pixel_to_world(0, 0)
        cornerRa = cornerSkyCoord.ra.to(u.rad)
        cornerDec = cornerSkyCoord.dec.to(u.rad)

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

        unitRadius = np.linalg.norm(unitSphereCenter - unitSphereCorner)
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
        **kwargs : `dict`
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

        Notes
        -----
        Implementation is standardizer-specific.
        """
        raise NotImplementedError()

    @classmethod
    def getStandardizer(cls, header, **kwargs):
        """Get the standardizer class that can handle given header.

        Parameters
        ----------
        header : `object`
             The header, Astropy HDU and its derivatives.
        **kwargs : `dict`
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
        """
        standardizers = []
        for standardizer in cls.standardizers.values():
            if standardizer.canStandardize(header):
                standardizers.append(standardizer)

        def get_priority(standardizer):
            """Return standardizers priority."""
            return standardizer.priority

        standardizers.sort(key=get_priority, reverse=True)

        if standardizers:
            if len(standardizers) > 1:
                # I think this should never be an issue really, but just in case
                names = [proc.name for proc in standardizers]
                logger.info("Multiple standardizers declared ability to process "
                            f"the given upload: {names}. Using {names[-1]} "
                            "to process FITS.")
            return standardizers[0]
        else:
            raise ValueError("None of the known standardizers can handle this upload.\n "
                             f"Known standardizers: {list(cls.standardizers.keys())}")

    @classmethod
    def fromHeader(cls, header, **kwargs):
        """Get the standardizer instance from a given header.

        Parameters
        ----------
        header : `object`
             The header, Astropy HDU and its derivatives.
        **kwargs : `dict`
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
            None of the registered processors can process the upload.
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
        standardizedHeaderMetadata : `upload.model.Metadata`
            Metadata object containing standardized values.

        Notes
        -----
        Implementation is instrument-specific.
        """
        raise NotImplementedError()

    def standardizeWcs(self, hdu=None):
        """Standardize WCS data a given header.

        Parameters
        ----------
        hdu : `object` or `None`, optional
            An Astropy image-like HDU unit. Useful when dealing with
            mutli-extension fits files where metadata is in the PrimaryHDU but
            the WCS and image data are stored in the extensions.

        Returns
        -------
        standardizedWCS : `upload.models.Wcs`
            Standardized WCS keys and values.

        Raises
        ------
        StandardizeWcsException
            there is no astrometry.net key in the file
        StandardizeWcsException
            no file WCS information could be found from sending to astrometry.net
        TimeoutError
            If it does not find a solution with the given time. Does not mean
            that astrometry.net cannot solve it.
        TypeError
            Some error in fits file preventing astrometry.net from working
        FileNotFoundError
            File not found from the path to file

        Notes
        -----
        Tries to read the WCS from the header.
        if that does not work then gives it to astrometry.net to look for a solution for the WCS
        """
        try:
            wcs = self._astropyWcsReader(hdu)
        except ValueError and TypeError:
            wcs = self._astrometryNetSolver(self.filename)# file path here
        return wcs

    def _astropyWcsReader(self, hdu=None):
        """Standardize WCS data a given header.

        Parameters
        ----------
        hdu : `object` or `None`, optional
            An Astropy image-like HDU unit. Useful when dealing with
            mutli-extension fits files where metadata is in the PrimaryHDU but
            the WCS and image data are stored in the extensions.

        Returns
            -------
            standardizedWCS : `upload.models.Wcs`
            Standardized WCS keys and values.

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

        Notes
        -----
        Standardized values are the are the Cartesian components of the central
        and corner pixels on the image, projected onto a unit sphere, and the
        distance between them.
        The center pixel coordinates is determined from header `NAXIS` keys,
        when possible, and is otherwise determined from the dimensions of the
        image in the given HDU.
        The (0, 0) pixel is taken as the corner pixel.
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

        wcs = models.Wcs(**self._computeStandardizedWcs(header, dimX, dimY))
        return wcs

    def _astrometryNetSolver(self, path_to_file):
        """Given a fits file it will process and send to astrometry.net
        where it will obtain the WCS data for the file if it is able to.
        If not then it will return an empty dictionary
        (this can be altered to whatever needs to be used for)

        Parameters
        ----------
        path_to_file : `string`
            path to the fits file

        Returns
        -------
        header : `dict`
            returns the header with the WCS data in it if it was found.
            If an error occurred or no solution is found then returns an empty dictionary.

        Raises
        ------
        StandardizeWcsException
            Found no solution from astrometry.net
        StandardizeWcsException
            There is no astrometry.net key
        TimeoutError
            If it does not find a solution with the given time. Does not mean
            that astrometry.net cannot solve it.
        TypeError
            Some error in fits file preventing astrometry.net from working
        FileNotFoundError
            File not found from the path to file

        Notes
        -----
        Send the file to astrometry.net to find WCS from the location of the stars in the image
        """
        dimX, dimY = fits.open(path_to_file).data.shape
        if ASTROMETRY_KEY:
            header = ASTRONET_CLIENT.solve_from_image(path_to_file, False, solve_timeout=200)
            if header == {}:
                raise StandardizeWcsException("Could not find WCS from fits file")
        else:
            raise StandardizeWcsException("There is no astrometry.net key")
        wcs = models.Wcs(**self._computeStandardizedWcs(header, dimX, dimY))
        return wcs


class StandardizeWcsException(Exception):
    """Exception raised when error in WCS processing

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="The WCS is not valid"):
        self.message = message
        super().__init__(self.message)
