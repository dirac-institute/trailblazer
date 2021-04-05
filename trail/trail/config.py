import os
import stat

import yaml


__all__ = ["CONF_FILE_ENVVAR", "CONF_FILE_PATH", "Config"]


CONF_FILE_ENVVAR = "TARILBLAZER_CONFIG"
"""Default name of the environmental variable that contains the path to the
configuration file. When the env var does not exist, configuration is assumed
to exist at its default location (see ``CONF_FILE_PATH``)."""

CONF_FILE_PATH = "~/.trail/config.yaml"
"""Default path at which it is expected the config file can be found. Will be
ignored if ``CONF_FILE_ENVVAR`` env var exists."""


class Config():
    """Represents a general YAML configuration file, with keys being mapped to
    attributes.

    Parameters
    ----------
    confDict : `dict`
        Dictionary whose keys will be mapped to attributes of the class.
    """
    def __init__(self, confDict):
        self._keys = []
        self._subConfs = []
        self._recurseDownDicts(confDict)

    def _recurseDownDicts(self, confDict):
        """Recursively walks the dictionary keys and values and maps keys to
        instance attributes.

        Parameters
        ----------
        confDict : `dict`
            Dictionary whose keys will be mapped to attributes of the class.
        """
        for key, val in confDict.items():
            if isinstance(val, dict):
                self._subConfs.append(key)
                setattr(self, key, Config(val))
            else:
                self._keys.append(key)
                setattr(self, key, val)

    def __repr__(self):
        reprStr = "Config("

        for key in self._subConfs:
            reprStr += f"{key}={getattr(self, key)}, "

        for key in self._keys:
            reprStr += key + ", "
        reprStr = reprStr[:-2]

        return reprStr+")"


    def __eq__(self, other):
        equal = True

        for key, subConf in zip(self._keys, self._subConfs):
            try:
                equal = equal and getattr(self, key) == getattr(other, key)
                equal = equal and getattr(self, subConf) == getattr(other, subConf)
            except AttributeError:
                # other does not have a key, but self has - not equal
                # or other does not have a subConf, but self has - not equal
                return False

        return equal


    @classmethod
    def fromYaml(cls, filePath=None):
        """Create a new Config instance from a YAML file.

        Parameters
        ----------
        filePath : `str` or `None`, Optional
            A file path to the YAML configuration. When not specified, first
            the ``CONF_FILE_ENVVAR`` is used. If it doesn't exist the
            ``CONF_FILE_PATH`` is used.
        """
        # resolve config file path
        if filePath is None:
            if CONF_FILE_ENVVAR in os.environ:
                filePath = os.path.expanduser(os.environ[CONF_FILE_ENVVAR])
            else:
                filePath = os.path.expanduser(CONF_FILE_PATH)

        # make sure file exists and its permissions are at 600 or more
        if not os.path.isfile(filePath):
            raise FileNotFoundError(f"No configuration file found: {filePath}")

        mode = os.stat(filePath).st_mode
        if mode & (stat.S_IRWXG | stat.S_IRWXO) != 0:
            raise PermissionError(f"Configuration file {filePath} has "
                                  f"incorrect permissions: {mode:o}")

        with open(filePath, 'r') as stream:
            confDict = yaml.safe_load(stream)

        return cls(confDict)
