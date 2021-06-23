"""
Defines the database schema used by trailblazer as well as some classes that
support working with the data. 
"""


from dataclasses import dataclass, make_dataclass, field, InitVar, asdict

from django.db import models
import numpy as np


__all__ = ["UploadInfo", "Metadata", "Wcs", "StandardizedHeader"]


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

    requiredKeys = []
    """Standardized keys that must exist if the result is to be recorded in the
    database.
    """

    def __init__(self, *args, **kwargs):
        # this is such an ugly hack, but Django ORM is so inflexible
        if not self.keys or self.requiredKeys:
            self.__set_keys()

    @classmethod
    def fromDictSubset(cls, data):
        """Create an instance from, potentially a subset of, dictionary
        elements that are also found in `keys`.

        Parameters
        ----------
        data : `dict`
            Dictionary from which to instantiate. Should contain at least the
            keys found in `requiredKeys`.

        Returns
        -------
        instance : `object`
            Instance created from given data.
        """
        dictSubset = {key: data.get(key, None) for key in cls.keys}
        return cls(**dictSubset)

    def __set_keys(self):
        """Read the model schema and add the defined fields to `keys` when the
        field is not a relationship or an auto generated field.
        Fields that are neither, and are also required to be not-null are added
        to the `requiredKeys`.
        """
        columns = [column for column in self._meta.get_fields()]
        names, required = [], []
        for col in columns:
            if not col.auto_created and not col.is_relation:
                names.append(col.name)
                if not col.null:
                    required.append(col.name)

        self.keys = names
        self.requiredKeys = required

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

    def isClose(self, other, **kwargs):
        """Tests approximate equality between objects.

        Parameters
        ----------
        other : `Metadata`
            Another `Metadata` instance to test approximate equality with.
        \**kwargs : `dict`
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
        areClose = np.allclose(
            [getattr(self, key) for key in self._closeEqualityKeys],
            [getattr(other, key) for key in other._closeEqualityKeys],
            **kwargs
        )
        return areEqual and areClose


class Wcs(models.Model, StandardizedKeysMixin):
    """Model schema for standardized WCS entries.
    There are potentially many WCS values associated with a single Metadata
    entry.
    """

    _closeEqualityKeys = ['wcs_radius', 'wcs_center_x', 'wcs_center_y',
                          'wcs_center_z', 'wcs_corner_x', 'wcs_corner_y',
                          'wcs_corner_z']
    """Standardized keys that are tested only in approximate equality."""

    # same as above, cascading can orphan WCS entries
    metadata = models.ForeignKey(Metadata, on_delete=models.PROTECT)

    wcs_radius = models.FloatField("distance between center and corner pixel")

    wcs_center_x = models.FloatField("unit sphere coordinate of central pixel")
    wcs_center_y = models.FloatField("unit sphere coordinate of central pixel")
    wcs_center_z = models.FloatField("unit sphere coordinate of central pixel")

    wcs_corner_x = models.FloatField("unit sphere coordinate of corner pixel")
    wcs_corner_y = models.FloatField("unit sphere coordinate of corner pixel")
    wcs_corner_z = models.FloatField("unit sphere coordinate of corner pixel")


    def isClose(self, other, **kwargs):
        """Tests approximate equality between objects.

        Parameters
        ----------
        other : `Metadata`
            Another `Metadata` instance to test approximate equality with.
        \**kwargs : `dict`
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
        return np.allclose(self.values(), other.values(), **kwargs)


class Thumbnails(models.Model):
    """Model schema for gallery thumbnails.
    Each WCS has an associated thumbnail.
    """
    wcs = models.OneToOneField(Wcs, on_delete=models.CASCADE, primary_key=True)
    large = models.CharField("location of large thumbnail", max_length=20)
    small = models.CharField("location of small thumbnail", max_length=20)


@dataclass
class StandardizedHeader:
    """A dataclass that associates standardized metadata with one or more
    standardized WCS.
    """
    metadata: Metadata = None
    wcs: list[Wcs] = field(default_factory=list)

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
            # otherwsie we expect a list.
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

    def _dataToComponent(self, data, component):
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
                compValuye = component.fromDictSubset(data)
        elif isinstance(data, component):
            compValue = data

        return compValue

    def updateMetadata(self, standardizedMetadata):
        """Update metadata values from a dictionary or another Metadata object.

        Parameters
        ----------
        standardizedMetadata : `dict` or `Metadata`
            All, or subset of all, metadata keys which values will be updated.
        """
        metadata = self._dataToComponent(standardizedMetadata, Metadata)
        if metadata is not None:
            self.metadata = metadata
        else:
            raise ValueError("Could not create metadata from the given data!")

    def appendWcs(self, standardizedWcs):
        """Append another WCS component.

        Parameters
        ----------
        standardizedWcs : `dict` or `Wcs`
            Data which to append to the current collection of associated wcs's.
        """
        wcs = self._dataToComponent(standardizedWcs, Wcs)
        if wcs is not None:
            wcs.metadata = self.metadata
            self.wcs.append(wcs)
        else:
            raise ValueError("Could not create metadata from the given data!")

    def extendWcs(self, standardizedWcs):
        """Extend current collection of associated wcs by appending elements
        from the iterable.

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
        \**kwargs : `dict`
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
            areClose = areClose and thisWcs.isClose(otherWcs)

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

    def save(self):
        """Insert standardized metadata and wcs data into the database."""
        self.metadata.save()

        # just in case Wcs was appended before metadata, set them explicitly
        for wcs in self.wcs:
            wcs.metadata = self.metadata
            wcs.save()

        # TODO: this doesn't work?
        #Wcs.objects.bulk_create(self.wcs)

