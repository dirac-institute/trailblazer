import os
from pathlib import Path
import stat

import yaml
import boto3


__all__ = ["CONF_FILE_ENVVAR", "CONF_FILE_PATH", "get_secrets_filepath",
           "Config", "SecretsConfig"]


CONF_FILE_ENVVAR = "TARILBLAZER_CONFIG"
"""Default name of the environmental variable that contains the path to the
configuration file. When the env var does not exist, configuration is assumed
to exist at its default location (see ``CONF_FILE_PATH``)."""

CONF_FILE_PATH = "~/.trail/secrets.yaml"
"""Default path at which it is expected the config file can be found. Will be
ignored if ``CONF_FILE_ENVVAR`` env var exists."""


def get_secrets_filepath():
    """Returns the resolved path of the secrets file. The path to the secrets
    file is resolved by checking:
        1) if `CONF_FILE_ENVVAR` (default: TRAILBLAZER_CONIFG) exists in the
           environmental variables. If it exists, the value of the variable
           is used as the default location of secrets file.
        2) if the env var is not set then `CONF_FILE_PATH` variable value is
           used as the default location of the secrets
           (default: ~/.trail/secrets)
    """
    if CONF_FILE_ENVVAR in os.environ:
        filePath = os.path.expanduser(os.environ[CONF_FILE_ENVVAR])
    else:
        filePath = os.path.expanduser(CONF_FILE_PATH)

    return filePath


def yaml_to_dict(filePath):
    """Reads given YAML file and returns a dictionary.

    Parameters
    ----------
    filePath : `str`
        Path to the YAML file.

    Returns
    -------
    confDict : `dict`
        Dictionary of YAML key-value pairs.
    """
    if not os.path.isfile(filePath):
        raise FileNotFoundError(f"No configuration file found: {filePath}")

    with open(filePath, 'r') as stream:
        confDict = yaml.safe_load(stream)

    return confDict


def fetch_aws_secrets(name, region):
    """Fetches a secret from AWS Secrets Manager and returns it as a dictionary

    Parameters
    ----------
    name : `str`
        Name of the secret.
    region : `str`
        AWS region the secret was stashed in.

    Returns
    -------
    secret : `dict`
        Secret fetched from AWS Secrets Manager.
    """
    smClient = boto3.client("secretsmanager", region_name=region)
    secretString = smClient.get_secret_value(SecretId=name)["SecretString"]
    # JSON is like YAML, right?
    return yaml.safe_load(secretString)


class Config():
    """Represents a general YAML configuration file. YAML keys are mapped to
    class attributes.

    Parameters
    ----------
    confDict : `dict`, optional
        Dictionary whose keys will be mapped to attributes of the class.
    """

    defaults = {}
    """Default instantiation values."""

    def __init__(self, confDict=None):
        if confDict is None:
            confDict = self.defaults
        self._keys = []
        self._subConfs = []
        self._recurseDownDicts(confDict)

    def _recurseDownDicts(self, confDict):
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
        for key, val in confDict.items():
            if isinstance(val, dict):
                self._subConfs.append(key)
                # class to underlying class here is important for inheritance
                setattr(self, key, self.__class__(val))
            else:
                self._keys.append(key)
                setattr(self, key, val)

    @classmethod
    def fromYaml(cls, filePath):
        """Create a new Config instance from a YAML file.

        Parameters
        ----------
        filePath : `str` or `None`, Optional
            A file path to the YAML configuration. When not specified, first
            the ``CONF_FILE_ENVVAR`` is used. If it doesn't exist the
            ``CONF_FILE_PATH`` is used.
        """
        return cls(yaml_to_dict(filePath))

    def __repr__(self):
        reprStr = f"{self.__class__.__name__}("

        for key in self._subConfs:
            reprStr += f"{key}={getattr(self, key)}, "

        for key in self._keys:
            reprStr += f"{key}={getattr(self, key)}, "
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
            res = {key.upper(): getattr(self, key) for key in self._keys}
        elif self._keys:
            res = {key: getattr(self, key) for key in self._keys}
        else:
            res = {}

        for subKey in self._subConfs:
            subDict = getattr(self, subKey).asDict(capitalizeKeys=capitalizeKeys)
            subKey = subKey.upper() if capitalizeKeys else subKey
            res[subKey] = subDict

        return res


class SecretsConfig(Config):
    """Represents a general YAML configuration file. YAML keys are mapped to
    class attributes.

    Parameters
    ----------
    confDict : `dict`, optional
        Dictionary whose keys will be mapped to attributes of the class.
    useAwsSecrets : `bool`, optional
        Resolve secrets using AWS Secrets manager. False by default.
    awsRegion : `str`, optional
        Region of the secret manager to use. Can be provided as a key in the
        config dictionary. Default: `us-west-2`.

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

    resolveKeys = ["secret_key", "secret_name"]
    """Specifies which keys are to be resolved as secrets."""

    secrets = ["secret_key", "USER", "PASSWORD", "NAME", "PORT"]
    """Keys that will be kept secrets in repr and str."""

    defaultAwsRegion = "us-west-2"
    """Specifies default AWS Region when AWS Secrets Manager is used."""

    defaults = {
        'db': {
            "engine": "django.db.backends.sqlite3",
            "name": str(Path(__file__).resolve().parent.parent.parent.joinpath("db.sqlite3"))
            },
        "secret_key": "alalala",
    }
    """Default instantiation values."""

    def __init__(self, confDict=None, useAwsSecrets=False, awsRegion=None):
        if confDict is None:
            confDict = self.defaults
        self._keys = []
        self._subConfs = []
        self._recurseDownDicts(confDict, useAwsSecrets, awsRegion)

    def _resolveAwsSecrets(self, confDict, region):
        """Recursively walks the dictionary keys looking for keys that appear
        in the `self.resolveKeys` list and resolves them by fetching the secret
        from AWS Secret Manager.

        When the returned secret is multi-keyed, the secret is unravelled and
        its contituent key-value pairs are inserted into the config dictionary,
        replacing the existing key.

        When the returned secret is a single key (a string) the resolved value
        is inserted under the existing key.

        Parameters
        ----------
        confDict : `dict`
            Configuration dictionary with unresolved secrets.
        region : `str`
            AWS Region where the secret was stored.

        Returns
        -------
        resolvedConfigDict : `dict`
            Config dictionary with resolved secrets.
        """
        resConf = confDict.copy()
        for key, val in confDict.items():
            if isinstance(val, dict):
                resConf[key] = self._resolveAwsSecrets(val, region)
            else:
                if key in self.resolveKeys:
                    secrets = fetch_aws_secrets(val, region)
                    if isinstance(secrets, dict):
                        # remove old secret_name key
                        resConf.pop(key, None)
                        for secretkey, secretval in secrets.items():
                            resConf[secretkey] = secretval
                    else:
                        resConf[key] = secrets

        return resConf

    def _recurseDownDicts(self, confDict, useAwsSecrets=False, awsRegion=None):
        """Recursively walks the dictionary keys and values and maps keys to
        instance attributes, resolving any existing secrets along the way.

        Parameters
        ----------
        confDict : `dict`
            Dictionary whose keys will be mapped to attributes of the class.
        useAwsSecrets : `bool`, optional
            Resolve secrets using AWS Secrets manager. False by default.
        awsRegion : `str` or `None`, optional
            AWS Region in which to look for the secret, region provided as part
            of the config dictionary take precendence over explicitly provided
            regions. If no AWS region is given here or in the config dictionary
            the default aws region is used.
        """
        if awsRegion:
            region = awsRegion
        else:
            region = confDict.get("aws-region", self.defaultAwsRegion)

        if useAwsSecrets:
            confDict = self._resolveAwsSecrets(confDict, region)

        super()._recurseDownDicts(confDict)

    @classmethod
    def fromYaml(cls, filePath, useAwsSecrets=False, awsRegion=None):
        """Create a new Config instance from a YAML file.

        Parameters
        ----------
        filePath : `str`
            A file path to the YAML configuration.
        useAwsSecrets : `bool`, optional
            Resolve secrets using AWS Secrets manager. False by default.
        awsRegion : `str` or `None`, optional
            AWS Region in which to look for the secret, region provided as part
            of the config dictionary take precendence over explicitly provided
            regions. If no AWS region is given here or in the config dictionary
            the default aws region is used.
        """
        mode = os.stat(filePath).st_mode
        if mode & (stat.S_IRWXG | stat.S_IRWXO) != 0:
            raise PermissionError(f"Configuration file {filePath} has "
                                  f"incorrect permissions: {mode:o}")

        confDict = yaml_to_dict(filePath)
        return cls(confDict, useAwsSecrets, awsRegion)

    def __repr__(self):
        reprStr = super().__repr__()

        for key in self.secrets:
            val = str(getattr(self, key, False))
            if val:
                reprStr = reprStr.replace(val, "****")

        return reprStr
