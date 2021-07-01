import os
from pathlib import Path
import stat

import yaml
import boto3


__all__ = ["CONF_FILE_ENVVAR", "CONF_FILE_PATH", "Config"]


CONF_FILE_ENVVAR = "TARILBLAZER_CONFIG"
"""Default name of the environmental variable that contains the path to the
configuration file. When the env var does not exist, configuration is assumed
to exist at its default location (see ``CONF_FILE_PATH``)."""

CONF_FILE_PATH = "~/.trail/secrets.yaml"
"""Default path at which it is expected the config file can be found. Will be
ignored if ``CONF_FILE_ENVVAR`` env var exists."""


class Config():
    """Represents a general YAML configuration file, with keys being mapped to
    attributes. Optionally resolving existing secrets via AWS Secrets Manager.

    Parameters
    ----------
    confDict : `dict`, optional
        Dictionary whose keys will be mapped to attributes of the class.
    useAwsSecrets : `bool`, optional
        Resolve secrets using AWS Secrets manager. False by default.
    awsRegion : `str`, optional
        Region of the secret manager to use. Default: `us-west-2`.

    Notes
    -----
    Secrets Manager can and will support any kind of string as a secret. For
    RDS it will tests showed that secrets are stored as a JSON key-value string
    pairs (i.e. output looks like a ``str(dict)``). This presents 3 different
    scenarios when keys get resolved and set as Config attributes:
    1) resolve a secret key into multiple keys and insert them, replacing the
       secret key with the recieved key-value pairs;
    2) resolve a secret and insert under original key, when returned  secrets
       are simple strings so the name of the secret is replaced with the secret
       itself;
    3) and insert a key-value pair named in the YAML config file.
    """

    configKey = "*"
    """Key which is read to create a config, the value `*` selects all keys."""

    secretsKeys = []
    """Specifies which keys are to be resolved as secrets."""

    defaults = {}
    """Default instantiation values."""

    def __init__(self, confDict=None, useAwsSecrets=False, awsRegion="us-west-2"):
        if confDict is None:
            confDict = {self.configKey: self.defaults}
        self._keys = []
        self._subConfs = []
        self._recurseDownDicts(confDict, useAwsSecrets, awsRegion=awsRegion)

    def _recurseDownDicts(self, confDict, useAwsSecrets, awsRegion):
        """Recursively walks the dictionary keys and values and maps keys to
        instance attributes, resolving any existing secrets along the way.

        Parameters
        ----------
        confDict : `dict`
            Dictionary whose keys will be mapped to attributes of the class.
        useAwsSecrets : `bool`, optional
            Resolve secrets using AWS Secrets manager. False by default.
        awsRegion : `str`, optional
            Region of the secret manager to use. Default: `us-west-2`.
        """
        if self.configKey != "*":
            if self.configKey not in confDict:
                raise ValueError(f"Required config key {self.configKey} does "
                                 "not exist in the config dictionary.")
            confDict = confDict[self.configKey]

        # if a region is set in the config use it, otherwise use the default
        region = confDict.get("aws-region", awsRegion)

        for key, val in confDict.items():
            if isinstance(val, dict):
                self._subConfs.append(key)
                setattr(self, key, Config(val))
            else:
                # of course this is now ugly...
                if useAwsSecrets and key in self.secretsKeys:
                    secrets = self._parseAwsSecrets(val, region)
                    if isinstance(secrets, dict):
                        # scenario 1, replacing key with many
                        for secretkey, secretval in secrets.items():
                            if secretkey not in self._keys:
                                self._keys.append(secretkey)
                            setattr(self, secretkey, secretval)
                        # skip inserting the replaced key
                        continue
                    else:
                        # scenario 2, resolve simple secret as key
                        val = secrets
                # scenario 2 or 3, insert key-value pair, resolving secrets
                self._keys.append(key)
                setattr(self, key, val)

    @staticmethod
    def _parseAwsSecrets(name, region):
        smClient = boto3.client("secretsmanager", region_name=region)
        secretString = smClient.get_secret_value(SecretId=name)["SecretString"]
        # JSON is like YAML, right?
        return yaml.safe_load(secretString)

    def __repr__(self):
        reprStr = f"{self.__class__.__name__}("

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

    def asDict(self, capitalizeKeys=False):
        """Returns the Conf as a dictionary.

        Parameters
        ----------
        capitalizeKeys : bool
            Capitalize all keys (does not captalize values). Sometimes it's
            usefull to capitalize just the keys when returning as dict in
            order for them to be used in Django configuration file.

        Returns
        -------
        config : `dict`
            Config object as a Python dictionary.
        """
        if capitalizeKeys:
            res = {key.upper():getattr(self, key) for key in self._keys}
        elif self._keys:
            res = {key:getattr(self, key) for key in self._keys}
        else:
            res = {}

        for subKey in self._subConfs:
            subDict = getattr(self, subKey).asDict(capitalizeKeys=capitalizeKeys)
            subKey = subKey.upper() if capitalizeKeys else subKey
            res[subKey] = subDict

        return res

    @classmethod
    def fromYaml(cls, filePath=None, useAwsSecrets=False, awsRegion="us-west-2"):
        """Create a new Config instance from a YAML file. By default will
        look at location pointed to by the environmental variable named by
        `CONF_FILE_ENVVAR`. If the env var is not set it will default to
        location set by `CONF_FILE_PATH`.

        Parameters
        ----------
        filePath : `str` or `None`, Optional
            A file path to the YAML configuration. When not specified, first
            the ``CONF_FILE_ENVVAR`` is used. If it doesn't exist the
            ``CONF_FILE_PATH`` is used.
        useAwsSecrets : `bool`, optional
            Resolve secrets using AWS Secrets manager. False by default.
        awsRegion : `str`, optional
            Region of the secret manager to use. Default: `us-west-2`.
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

        return cls(confDict, useAwsSecrets, awsRegion)


class DbAuth(Config):
    configKey = 'db'
    secretsKeys = ["secret_name", ]
    defaults = {
        "engine": "django.db.backends.sqlite3",
        "name": str(Path(__file__).resolve().parent.parent.parent.joinpath("db.sqlite3"))
    }

    def asDict(self):
        return super().asDict(capitalizeKeys=True)


class SiteConfig(Config):
    configKey = 'settings'
    secretsKeys = ["secret_key", ]
    defaults = {
        "secret_key" : "alalala"
    }
