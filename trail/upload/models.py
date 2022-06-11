"""
Defines the database schema used by trailblazer as well as some classes that
support working with the data.
"""


import os
from dataclasses import dataclass, field
from typing import Sequence

from django.db import models
from django.conf import settings

from query.coord_conversion import getXYZFromWcs

from PIL import Image
import numpy as np


__all__ = ["UploadInfo", "Metadata", "Wcs", "StandardizedHeader"]


def set_keys_from_columns(cls):
    """Read the model schema and add fields, that are not a relationship or an
    auto-generated field, to class attribute `keys`.
    Added fields that are also not nullable to the `required_keys` class
    attribute.

    Parameters
    -----------
    cls : `class`
        Class to inspect and modify.
    """
    # This is quite hacky, but I honestly could not find a different way and
    # have Django not complain about un-initialized models, or completely
    # breaking down the models __init__ method...
    if cls.keys or cls.required_keys:
        return  # this should really perhaps be an error?

    columns = [column for column in cls._meta.get_fields()]
    names, required = [], []
    for col in columns:
        if not col.auto_created and not col.is_relation:
            names.append(col.name)
            if not col.null:
                required.append(col.name)

    cls.keys = names
    cls.required_keys = required


def dataToComponent(data, component):
    """Converts data to the desired component.

    Parameters
    ----------
    data : `dict`, `object`
        Data from which the component will be constructed. This can be an
        dictionary with keys that are exact match for parameters required
        by component, or a superset, or could be an instance of component
        already.
    component : `cls`
        Class the data will convert to.
    """
    compValue = None
    if isinstance(data, dict):
        try:
            compValue = component(**data)
        except KeyError:
            compValue = component.fromDictSubset(data)
    elif isinstance(data, component):
        compValue = data

    return compValue


class UploadInfo(models.Model):
    """Records originator and time of upload of an sngle metadata entry. """
    # integer autoincrement primary fields is automatically added by Django
    created = models.DateTimeField("date on which data was uploaded", auto_now_add=True)
    ip = models.GenericIPAddressField("IP address of the uploader", default="127.0.0.1")


class StandardizedKeysMixin:
    """Mix-in class for standardized output data classes.
    """

    keys = []
    """All standardized keys expected as output of processing."""

    required_keys = []
    """Standardized keys that must exist if the result is to be recorded in the
    database.
    """

    @classmethod
    def fromDictSubset(cls, data):
        """Create an instance from, potentially a subset of, dictionary
        elements that are also found in `keys`.

        Parameters
        ----------
        data : `dict`
            Dictionary from which to instantiate. Should contain at least the
            keys found in `required_keys`.

        Returns
        -------
        instance : `object`
            Instance created from given data.
        """
        dictSubset = {key: data.get(key, None) for key in cls.keys}
        return cls(**dictSubset)

    def values(self):
        """Returns a list of `keys` values."""
        return [getattr(self, key) for key in self.keys]

    def toDict(self):
        """Returns a dictionary of `keys` names and values."""
        # asdict use here would be nice, but is much slower...
        return {key: getattr(self, key) for key in self.keys}


class Metadata(models.Model, StandardizedKeysMixin):
    """Model schema for standardized primary HDU metadata.
    A single upload can have many associated metadata entries.
    """

    _closeEqualityKeys = ['obs_lon', 'obs_lat', 'obs_height']
    """Standardized keys that are tested only in approximate equality."""

    # This will need to be fixed, cascading can orphan metadata entries
    upload_info = models.ForeignKey(UploadInfo, on_delete=models.PROTECT)

    # verbose_names should be lowercase, Django will capitalize
    # https://docs.djangoproject.com/en/3.1/topics/db/models/#verbose-field-names
    processor_name = models.CharField("name of translator used to process FITS header information", max_length=20)
    standardizer_name = models.CharField("name of standardizer used to process FITS header information", max_length=20)
    instrument = models.CharField("instrument name", max_length=20, null=True)
    telescope = models.CharField("telescope", max_length=20, null=True)
    science_program = models.CharField("science program image is a part of.",
                                       max_length=30,
                                       null=True)

    obs_lon = models.FloatField("observatory longitude (deg)")
    obs_lat = models.FloatField("observatory latitude (deg)")
    obs_height = models.FloatField("observatory height (m)")

    datetime_begin = models.DateTimeField("UTC at exposure start.")
    datetime_end = models.DateTimeField("UTC at exposure end.")
    exposure_duration = models.FloatField("exposure time (s)", null=True)
    filter_name = models.CharField("filter name", max_length=30, null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_keys_from_columns(self.__class__)

    def isClose(self, other, **kwargs):
        """Tests approximate equality between objects.

        Parameters
        ----------
        other : `Metadata`
            Another `Metadata` instance to test approximate equality with.
        **kwargs : `dict`
            Keyword arguments passed onto `numpy.allclose`

        Returns
        -------
        approxEqual : `bool`
            True when approximately equal, False otherwise.

        Note
        ----
        Only values in `_closeEqualityKeys` will be tested approximately, the
        rest will be matched exactly.
        """
        exactlyMatched = list(set(self.keys) - set(self._closeEqualityKeys))
        areEqual = all([getattr(self, key) == getattr(other, key) for key in exactlyMatched])

        # when a value is None (not set) the equality still might hold
        # despite the fact the object is not valid but np will complain
        # about implicit casting, so we need to do it explicitly, luckily
        # all the vals are floats, but performance-wise it's better to fail?
        slfVals = [getattr(self, key) for key in self._closeEqualityKeys]
        othVals = [getattr(other, key) for key in other._closeEqualityKeys]
        try:
            areClose = np.allclose(slfVals, othVals, **kwargs)
        except TypeError:
            slfVals = np.array(slfVals, dtype=float)
            othVals = np.array(othVals, dtype=float)
            areClose = np.allclose(slfVals, othVals, **kwargs)

        return areEqual and areClose

    @classmethod
    def query_sky_region(cls, bboxDict, queryset=None):
        """Queries metadata in a sky region and returns
        the queryset.

        Parameters
        ----------
        bboxDict : `rest_framework.QueryDict` or `dict`
            Sky Bounding box. Must contain keys `raLow`, `raHigh`, `decLow`
            and `decHigh`
        queryset : `django.QuerySet` or `None`, optional
            If given, performs the query on the queryset,
            otherwise performs the query on all metadata.

        Returns
        -------
        queryset : `django.QuerySet`
            Metadata within the given bounding box.
        bboxDict :
            Given bounding box dictionary, with the required keys
            removed.

        Raises
        ------
        ValueError :
           When not all of the mandatory keys are present in the
           bounding box dictionary.

        Notes
        -----
        The bounding box dictionary can contain more keys than just the
        mandatory ones (`raLow`, `raHigh`, `decLow`, `decHigh`) which
        will be `.pop`-ed from the dictionary. We use this to filter
        down query keys in rest_api.
        """
        if not all(["raLow" in bboxDict, "raHigh" in bboxDict,
                    "decLow" in bboxDict, "decHigh" in bboxDict]):
            raise ValueError(
                "Insufficient sky region parameters were present. "
                "Requires `raLow`, `raHight`, `decLow` and `decHight` "
                "in decimal degrees."
            )

        if queryset is None:
            queryset = cls.objects.all()

        # pop them out, so that if there are any leftover qparams we can still
        # query on them as a regular filter
        raLow, raHigh = float(bboxDict.pop("raLow")), float(bboxDict.pop("raHigh"))
        decLow, decHigh = float(bboxDict.pop("decLow")), float(bboxDict.pop("decHigh"))

        lowerRight = getXYZFromWcs(raLow, decLow)
        upperLeft = getXYZFromWcs(raHigh, decHigh)

        wcsqparams = {
            "wcs__center_x__gte": upperLeft["x"],
            "wcs__center_x__lte": lowerRight["x"],
            "wcs__center_y__lte": upperLeft["y"],
            "wcs__center_y__gte": lowerRight["y"],
            "wcs__center_z__lte": upperLeft["z"],
            "wcs__center_z__gte": lowerRight["z"]
        }

        # add filtering on WCS information
        queryset = queryset.filter(**wcsqparams)

        # return the queryset for further filtering.
        return queryset, bboxDict


class Wcs(models.Model, StandardizedKeysMixin):
    """Model schema for standardized WCS entries.
    There are potentially many WCS values associated with a single Metadata
    entry.
    """

    _closeEqualityKeys = ['radius', 'center_x', 'center_y',
                          'center_z', 'corner_x', 'corner_y',
                          'corner_z']
    """Standardized keys that are tested only in approximate equality."""

    # same as above, cascading can orphan WCS entries
    metadata = models.ForeignKey(Metadata, related_name="wcs", on_delete=models.PROTECT)

    radius = models.FloatField("distance between center and corner pixel")

    center_x = models.FloatField("unit sphere coordinate of central pixel")
    center_y = models.FloatField("unit sphere coordinate of central pixel")
    center_z = models.FloatField("unit sphere coordinate of central pixel")

    corner_x = models.FloatField("unit sphere coordinate of corner pixel")
    corner_y = models.FloatField("unit sphere coordinate of corner pixel")
    corner_z = models.FloatField("unit sphere coordinate of corner pixel")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_keys_from_columns(self.__class__)

    def isClose(self, other, **kwargs):
        """Tests approximate equality between objects.

        Parameters
        ----------
        other : `Metadata`
            Another `Metadata` instance to test approximate equality with.
        **kwargs : `dict`
            Keyword arguments passed onto `numpy.allclose`

        Returns
        -------
        approxEqual : `bool`
            True when approximately equal, False otherwise.

        Note
        ----
        Only values in `_closeEqualityKeys` will be tested approximately, the
        rest will be matched exactly. For Wcs, these are keys.
        """
        try:
            return np.allclose(self.values(), other.values(), **kwargs)
        except TypeError:
            # same problem as in Metadata isClose
            slfVals = np.array(self.values(), dtype=float)
            othVals = np.array(other.values(), dtype=float)
            return np.allclose(slfVals, othVals, **kwargs)


class Thumbnails(models.Model, StandardizedKeysMixin):
    """Model schema for gallery thumbnails.
    Each WCS has an associated thumbnail.
    """
    SMALL_THUMB_ROOT = settings.SMALL_THUMB_ROOT
    """Root of the location where small thumbnails will be stored."""

    LARGE_THUMB_ROOT = settings.LARGE_THUMB_ROOT
    """Root of the location where large thumbnails will be stored."""

    wcs = models.OneToOneField(Wcs, on_delete=models.CASCADE, primary_key=True)
    large = models.CharField("relative location of large thumbnail", max_length=20)
    small = models.CharField("relative location of small thumbnail", max_length=20)

    # the manual says not to do this but I don't understand what the point of an
    # ORM is if I can't have instance attributes
    def __init__(self, *args, **kwargs):
        super(Thumbnails, self).__init__(*args, **kwargs)
        self._largeimg = kwargs.pop("largeimg", None)
        self._smallimg = kwargs.pop("smallimg", None)

    @property
    def largeAbsPath(self):
        """Absolute path to the large thumbnail."""
        return os.path.join(self.LARGE_THUMB_ROOT, self.large)

    @property
    def smallAbsPath(self):
        """Absolute path to the small thumbnail."""
        return os.path.join(self.SMALL_THUMB_ROOT, self.small)

    # this is more of a sketch than final code, it's unclear, to me, how not to
    # duplicate code or work in this class.... Consider punting the file IO
    # here as well
    @property
    def largeimg(self):
        """Large thumbnail image."""
        if self._largeimg is None:
            self._largeimg = self.get_img("large")
        return self._largeimg

    @property
    def smallimg(self):
        """Small thumbnail image."""
        if self._smallimg is None:
            self._smallimg = self.get_img("small")
        return self._largeimg

    def _specified_return(self, returnval, which):
        if which.lower() == "small":
            return returnval["small"]
        elif which.lower() == "large":
            return returnval["large"]
        else:
            return returnval

    def abspath(self, which=None):
        """Return absolute paths to the thumbnails.

        Parameters
        ----------
        which : `str`, optional
            Desired thumbnail, `small` or `large` or None, in which case a
            both are returned.

        Returns
        -------
        abspath : `str` or `dict`
            If `which` is given returns the desired path as a string, if which
            is `None` both paths are returned in a dictionary.
        """
        # TODO: abstract away in an URI class when transitioning
        # to S3
        returnval = {
            "large": self.largeAbsPath,
            "small": self.smallAbsPath
        }
        return self._specified_return(returnval, which)

    def get_img(self, which):
        """Return one of the thumbnail images as a Pil `Image` object.

        Parameters
        ----------
        which : `str`
            Desired thumbnail, `small` or `large`.

        Returns
        -------
        img : `PIL.Image`
            Requested image.
        """
        # TODO: add download to tmpdir for S3 if S3 URI
        # consider adding tonumpyarr kwarg or something
        path = self.abspath(which)
        return Image.open(path)


@dataclass
class StandardizedHeader:
    """A dataclass that associates standardized metadata with one or more
    standardized WCS.
    """
    metadata: Metadata = None
    wcs: Sequence[Wcs] = field(default_factory=list)

    @classmethod
    def fromDict(cls, data):
        """Construct an StandardizedHeader from a dictionary.

        The dictionary can contain either a flattened set of values like:

            {obs_lon: ... <metadata keys>, wcs_radius: ... <wcs_keys>}

        or have separated metadata and wcs values like:

            {metadata: {...}, wcs: {...}}

        in which case the wcs can be an iterable, i.e.

            {metadata: {...}, wcs: [{...}, {...}, ... ]}

        Parameters
        ----------
        data : `dict`
            Dictionary containing at least the required standardized keys for
            `Metadata` and `Wcs`.
        """
        meta, wcs = None, []
        if "metadata" in data and "wcs" in data:
            meta = Metadata(**data["metadata"])

            # sometimes multiExt Fits have only 1 valid image extension
            # otherwise we expect a list.
            if isinstance(data["wcs"], dict):
                wcs.append(Wcs(metadata=meta, **data["wcs"]))
            else:
                for ext in data["wcs"]:
                    wcs.append(Wcs(metadata=meta, **ext))
        else:
            meta = Metadata.fromDictSubset(data)
            wcs = Wcs.fromDictSubset(data)
            wcs.metadata = meta

        if type(wcs) != list:
            wcs = [wcs, ]

        return cls(metadata=meta, wcs=wcs)

    def __eq__(self, other):
        return self.isClose(other)

    @property
    def isMultiExt(self):
        """True when the header is a multi extension header."""
        return len(self.wcs) > 1

    def updateMetadata(self, standardizedMetadata):
        """Update metadata values from a dictionary or another Metadata object.

        Parameters
        ----------
        standardizedMetadata : `dict` or `Metadata`
            All, or subset of all, metadata keys which values will be updated.
        """
        metadata = dataToComponent(standardizedMetadata, Metadata)
        if metadata is not None:
            self.metadata = metadata
        else:
            raise ValueError(f"Could not create metadata from the given data: {standardizedMetadata}")

    def appendWcs(self, standardizedWcs):
        """Append a WCS component.

        Parameters
        ----------
        standardizedWcs : `dict` or `Wcs`
            Data which to append to the current collection of associated wcs's.
        """
        wcs = dataToComponent(standardizedWcs, Wcs)
        if wcs is not None:
            self.wcs.append(wcs)
        else:
            raise ValueError(f"Could not create a WCS from the given data: {standardizedWcs}")

    def extendWcs(self, standardizedWcs):
        """Extend current collection of associated wcs by appending elements
        from an iterable.

        Parameters
        ----------
        standardizedWcs : `iterable``
            Data which to append to the current collection of associated wcs's.
        """
        for wcs in standardizedWcs:
            self.appendWcs(wcs)

    def isClose(self, other, **kwargs):
        """Tests approximate equality between two standardized headers by
        testing appoximate equality of respective metadatas and wcs's.

        Parameters
        ----------
        other : `StandardizeHeader`
            Another `Metadata` instance to test approximate equality with.
        **kwargs : `dict`
            Keyword arguments passed onto `numpy.allclose`

        Returns
        -------
        approxEqual : `bool`
            True when approximately equal, False otherwise.
        """
        if len(self.wcs) != len(other.wcs):
            return False

        areClose = self.metadata.isClose(other.metadata, **kwargs)
        for thisWcs, otherWcs in zip(self.wcs, other.wcs):
            areClose = areClose and thisWcs.isClose(otherWcs, **kwargs)

        return areClose

    def toDict(self):
        """Returns a dictionary of standardized metadata and wcs values."""
        if self.isMultiExt:
            wcsDicts = {"wcs": [wcs.toDict() for wcs in self.wcs]}
        else:
            wcsDicts = {"wcs": self.wcs[0].toDict()}
        metadataDict = {"metadata": self.metadata.toDict()}
        metadataDict.update(wcsDicts)
        return metadataDict


@dataclass
class StandardizedResult:
    """A dataclass that associates standardized header metadata with one or
    more standardized WCS and their thumbnails.
    """
    _thumbkeys = ["thumbnails", "thumbs", "thumbnail", "thumb"]
    header: StandardizedHeader = None
    thumbnails: Sequence[Thumbnails] = field(default_factory=list)

    @classmethod
    def __resolve_thumbs(cls, data):
        """Resolve what format and under which commonly used abbreviation were
        the thumbs given in - a dict, a dict in a dict, a list of dicts etc -
        and then return them as a list of `Thumbnails` object(s).

        Parameters
        ----------
        data : `dict`
            Dictionary containing at least the required standardized keys for
            `Metadata`, `Wcs` and `Thumbnail`.

        Returns
        -------
        thumbs : `list`
            A list of one or more `Thumbnails` objects.
        """
        if isinstance(data, Thumbnails):
            return [data, ]

        # assume all of them are Thumbnails in a list and return
        try:
            if isinstance(data[0], Thumbnails):
                return data
        except TypeError:
            pass

        i = 0
        thumbnails = None
        while (thumbnails is None and i < len(cls._thumbkeys)):
            thumbnails = data.pop(cls._thumbkeys[i])
            i += 1

        # try one more time with a flat dict, just in case someone was too lazy
        # Otherwise, thumbnails were retrieved as a dict, or a list of dicts
        if thumbnails is None:
            large = data.pop("large", None)
            small = data.pop("small", None)
            thumbs = [Thumbnails(large=large, small=small), ]
        elif isinstance(thumbnails, dict):
            thumbs = [Thumbnails(large=large, small=small), ]
        else:
            thumbs = []
            for thumb in thumbnails:
                thumbs.append(Thumbnails(large=thumb["large"], small=thumb["small"]))

        return thumbs

    @classmethod
    def fromDict(cls, data):
        """Construct an StandardizedResult from a dictionary.

        The dictionary can contain either a flattened set of values of a single
        result f.e.:

            {obs_lon: ... <metadata keys>, wcs_radius: ... <wcs_keys>, large: ... <thumbnail_keys>}

        or have separated metadata, wcs and thumbnail keys like:

            {metadata: {...}, wcs: {...}, thumbnails: {...}}

        in which case the wcs and thumbnails can be iterable, i.e.

            {metadata: {...}, wcs: [{...}, {...}, ... ],  thumbnails: [{...}, {...}, ... ],}

        Parameters
        ----------
        data : `dict`
            Dictionary containing at least the required standardized keys for
            `Metadata`, `Wcs` and `Thumbnail`.
        """
        thumbs = cls.__resolve_thumbs(data)
        header = StandardizedHeader.fromDict(data)
        return cls(header=header, thumbnails=thumbs)

    def __eq__(self, other):
        return self.header.isClose(other)

    @property
    def wcs(self):
        """Standardized wcs."""
        return self.header.wcs

    @property
    def metadata(self):
        """Standardized metadata."""
        return self.header.metadata

    @property
    def isMultiExt(self):
        """True when the header is a multi extension header."""
        return len(self.wcs) > 1

    def appendThumbnail(self, thumbnail):
        """Append a Thumbnail to the end of the thumbnails list.

        Parameters
        -----------
        thumbnail: `dict`, `Thumbnail`
            Thumbnail or a data required to construct a Thumbnail object.
        """
        thumb = dataToComponent(thumbnail, Thumbnails)
        if thumb is not None:
            self.thumbnails.append(thumb)
        else:
            raise ValueError("Could not create a Thumbnail from the given data!")

    def extendThumbnails(self, thumbnails):
        """Extend thumbnails list by appending elements from an iterable.

        thumbnails: `list`
            Iterable containing Thumbnail objects or dicts with required data
            to construct a Thumbnail object.
        """
        for thumb in thumbnails:
            self.appendThumbnail(thumb)

    def toDict(self):
        """Returns a dictionary of standardized metadata, wcs an thumbnails."""
        metadataDict = self.header.toDict()
        if self.isMultiExt:
            thumbDicts = {"thumbnails": [thumb.toDict() for thumb in self.thumbnails]}
        else:
            thumbDicts = {"thumbnails": {"large": self.thumbnails[0].large,
                                         "small": self.thumbnails[0].small}}
        metadataDict.update(thumbDicts)
        return metadataDict
