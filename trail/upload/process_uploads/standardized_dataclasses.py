"""
Dataclasses for easier handling of processing results.

Handling processing results poses a slight problem in terms of handling
processing results, in that the processing steps do not map readily to the
models and yet it is neccessary, in testing, developing and debugging, to
compare these processing results to each other in an easier way than manually
cranking dictionaries.
"""


from abc import ABC
from dataclasses import dataclass, make_dataclass, field, InitVar, asdict
from typing import ClassVar

import numpy as np

import yaml


__all__ = ["StandardizedWcsKeys",
           "StandardizedMetadataKeys",
           "StandardizedHeaderKeys",]


dtype = np.dtype([("names", str, 30), ("types", object),  ("defaults", object),
                  ("required", bool),("closeEquality", bool)])

wcsAttributes = np.array([
    ("wcs_radius",   float, None, True, True),
    ("wcs_center_x", float, None, True, True),
    ("wcs_center_y", float, None, True, True),
    ("wcs_center_z", float, None, True, True),
    ("wcs_corner_x", float, None, True, True),
    ("wcs_corner_y", float, None, True, True),
    ("wcs_corner_z", float, None, True, True)],
                         dtype=dtype)

metaAttrs = np.array([
    ("obs_lon",                float, None, True,  True),
    ("obs_lat",                float, None, True,  True),
    ("obs_height",             float, None, True,  True),
    ("telescope",                str, None, True,  False),
    ("datetime_begin",           str, None, True,  False),
    ("datetime_end",             str, None, True,  False),
    ("metadata_translator_name", str, None, False, False),
    ("instrument",               str, None, False, False),
    ("science_program",          str, None, False, False),
    ("exposure_duration",        str, None, False, False),
    ("physical_filter",          str, None, False, False)],
                     dtype=dtype)


def get_dict_subset(data, keys):
    return {key: data.get(key, None) for key in keys}


class StandardizedKeysMixin:
    """Mix-in class for StandardizeKeys classes."""

    @classmethod
    def fromDictSubset(cls, data):
        """
        """
        return cls(**get_dict_subset(data, cls.keys))

    def values(self):
        return [getattr(self, key) for key in self.keys]

    def toDict(self):
        # asdict use here would be nice, but is much slower...
        return {key: getattr(self, key) for key in self.keys}

    def valid(self):
        for key, keytype in zip(self._requiredKeys, self.keyTypes):
            if not (getattr(self, key) and type(getattr(self, key)) == keytype):
                return False
        return True

@dataclass(order=True)
class StandardizedWcsBase(ABC, StandardizedKeysMixin):
    keys: ClassVar[list] = wcsAttributes["names"]
    keyTypes: ClassVar[list] = wcsAttributes["types"]
    _requiredKeys: ClassVar[list] = keys
    _closeEqualityKeys = keys

    def isCloseTo(self, other, **kwargs):
        return np.allclose(self.values(), other.values(), **kwargs)


@dataclass(order=True)
class StandardizedMetadataBase(ABC, StandardizedKeysMixin):
    keys: ClassVar[list] = metaAttrs["names"]
    keyTypes: ClassVar[list] = metaAttrs["types"]
    _closeEqualityKeys = metaAttrs[metaAttrs["closeEquality"] == True]["names"]

    _requiredKeys: ClassVar[list] = metaAttrs[metaAttrs["required"] == True]["names"]
    _optionalKeys: ClassVar[list] = metaAttrs[metaAttrs["required"] == False]["names"]

    def isCloseTo(self, other, **kwargs):
        exactlyMatched = list(set(self.keys) - set(self._closeEqualityKeys))
        areEqual = all([getattr(self, key) == getattr(other, key) for key in exactlyMatched])
        areClose = np.allclose(
            [getattr(self, key) for key in self._closeEqualityKeys],
            [getattr(other, key) for key in other._closeEqualityKeys],
            **kwargs
        )
        return areEqual and areClose


StandardizedWcsKeys = make_dataclass("StandardizedWcsKeys",
                                     fields=wcsAttributes[["names", "types"]],
                                     bases=(StandardizedWcsBase,))


StandardizedMetadataKeys = make_dataclass("StandardizedMetadataKeys",
                                          fields=metaAttrs[["names", "types", "defaults"]],
                                          bases=(StandardizedMetadataBase,))


@dataclass
class StandardizedHeaderKeys:
    metadata: StandardizedMetadataKeys = None
    wcs: list[StandardizedWcsKeys] = field(default_factory=list)
    isMulitExt: InitVar[bool] = False

    @classmethod
    def fromDict(cls, data, isMultiExt=False):
        meta, wcs = None, []
        #data = data.copy()

        if isMultiExt:
            # check if we were given long-format standardized header. In short
            # format, metadata and WCS data are separate. In long format they
            # are combined for each standardized header
            if "metadata" in data and "wcs" in data:
                # in short format, with mutli-ext, wcs is a dict keys of which
                # are indices of EXTs and values are standardized keys.
                meta = StandardizedMetadataKeys(**data["metadata"])
                for ext in data["wcs"]:
                    wcs.append(StandardizedWcsKeys(**ext))
            else:
                # in long format, with multi-ext, keys are indices of EXTs and
                # values contain both meta and wcs keys. 
                for key, val in data.items():
                    wcs.append(StandardizedWcsKeys.fromDictSubset(val))
                meta = StandardizedMetadataKeys.fromDictSubset(val)
        else:
            if "metadata" in data and "wcs" in data:
                # short format again
                meta = StandardizedMetadataKeys(**data["metadata"])
                wcs = StandardizedWcsKeys(**data["wcs"])
            else:
                # long format
                meta = StandardizedMetadataKeys.fromDictSubset(data)
                wcs = StandardizedWcsKeys.fromDictSubset(data)

        if type(wcs) != list:
            wcs = [wcs, ]

        return cls(metadata=meta, wcs=wcs)

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
        wcs = self._dataToComponent(standardizedWcs, StandardizedWcsKeys)
        if wcs is not None:
            self.wcs.append(wcs)
            #fix isMultiExt
            if len(self.wcs) > 1:
                self.isMultiExt = True
        else:
            raise ValueError("Could not create metadata from the given data!")

    def isCloseTo(self, other, **kwargs):
        if len(self.wcs) != len(other.wcs):
            return False

        areClose = self.metadata.isCloseTo(other.metadata, **kwargs)
        for thisWcs, otherWcs in zip(self.wcs, other.wcs):
            areClose = areClose and thisWcs.isCloseTo(otherWcs)

        return areClose

    def valid(self):
        if not self.metadata.valid():
            return False

        for wcs in self.wcs:
            if not wcs.valid():
                return False

        return True

    def toDict(self, short=True):
        if short:
            standardizedMetadata.update(standardizedWcs)
            return standardizedMetadata
        else:
            standardizedHeader = {}
            for key, val in standardizedWcs.values():
                standardizedHeader[key] = dict(standardizedMetadata["primary"],
                                               **val)
            return standardizedHeader


