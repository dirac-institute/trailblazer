from dataclasses import dataclass, make_dataclass, field, InitVar, asdict

from django.db import models
import numpy as np


"""Define the SQL metadata design here."""


__all__ = ["UploadInfo", "Metadata", "Wcs"]


class UploadInfo(models.Model):
    # integer autoincrement primary fields is automatically added by Django

    created = models.DateTimeField("date on which data was uploaded", auto_now_add=True)
    ip = models.GenericIPAddressField("IP address of the uploader", default="127.0.0.1")


class StandardizedKeysMixin:
    """Mix-in class for StandardizeKeys classes."""

    keys = []
    requiredKeys = []

    @classmethod
    def fromDictSubset(cls, data):
        dictSubset = {key: data.get(key, None) for key in cls.keys}
        return cls(**dictSubset)

    def __init__(self, *args, **kwargs):
        # this is such an ugly hack, but Django ORM is so inflexible
        if not self.keys or self.requiredKeys:
            self.__set_keys()

    def __set_keys(self):
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
        return [getattr(self, key) for key in self.keys]

    def toDict(self):
        # asdict use here would be nice, but is much slower...
        return {key: getattr(self, key) for key in self.keys}


class Metadata(models.Model, StandardizedKeysMixin):
    _closeEqualityKeys = ['obs_lon', 'obs_lat', 'obs_height']

    # This will need to be fixed, cascading can orphan medata entries
    upload_info = models.ForeignKey(UploadInfo, on_delete=models.PROTECT)

    # verbose_names should be lowercase, Django will capitalize
    # https://docs.djangoproject.com/en/3.1/topics/db/models/#verbose-field-names
    processor_name = models.CharField("name of used translator.", max_length=20)
    standardizer_name = models.CharField("name of used translator.", max_length=20)
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
    physical_filter = models.CharField("physical filter",
                                       max_length=30,
                                       null=True)

    def isClose(self, other, **kwargs):
        exactlyMatched = list(set(self.keys) - set(self._closeEqualityKeys))
        areEqual = all([getattr(self, key) == getattr(other, key) for key in exactlyMatched])
        areClose = np.allclose(
            [getattr(self, key) for key in self._closeEqualityKeys],
            [getattr(other, key) for key in other._closeEqualityKeys],
            **kwargs
        )
        return areEqual and areClose


class Wcs(models.Model, StandardizedKeysMixin):
    _closeEqualityKeys = ['wcs_radius', 'wcs_center_x', 'wcs_center_y',
                          'wcs_center_z', 'wcs_corner_x', 'wcs_corner_y',
                          'wcs_corner_z']

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
        return np.allclose(self.values(), other.values(), **kwargs)


class Thumbnails(models.Model):
    wcs = models.OneToOneField(Wcs, on_delete=models.CASCADE, primary_key=True)
    large = models.CharField("location of large thumbnail", max_length=20)
    small = models.CharField("location of small thumbnail", max_length=20)


@dataclass
class StandardizedHeader:
    metadata: Metadata = None
    wcs: list[Wcs] = field(default_factory=list)

    @classmethod
    def fromDict(cls, data):
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

    @property
    def isMultiExt(self):
        return len(self.wcs) > 1

    def _dataToComponent(self, data, component):
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
        metadata = self._dataToComponent(standardizedMetadata, StandardizedMetadataKeys)
        if metadata is not None:
            self.metadata = metadata
        else:
            raise ValueError("Could not create metadata from the given data!")

    def addWcs(self, standardizedWcs):
        wcs = self._dataToComponent(standardizedWcs, Wcs)
        if wcs is not None:
            wcs.metadata = self.metadata
            self.wcs.append(wcs)
            #fix isMultiExt
            if len(self.wcs) > 1:
                self.isMultiExt = True
        else:
            raise ValueError("Could not create metadata from the given data!")

    def isClose(self, other, **kwargs):
        if len(self.wcs) != len(other.wcs):
            return False

        areClose = self.metadata.isClose(other.metadata, **kwargs)
        for thisWcs, otherWcs in zip(self.wcs, other.wcs):
            areClose = areClose and thisWcs.isClose(otherWcs)

        return areClose

    def toDict(self):
        if self.isMultiExt:
            wcsDicts = {"wcs": [wcs.toDict() for wcs in self.wcs]}
        else:
            wcsDicts = {"wcs": self.wcs[0].toDict()}
        metadataDict = {"metadata": self.metadata.toDict()}
        metadataDict.update(wcsDicts)
        return metadataDict

