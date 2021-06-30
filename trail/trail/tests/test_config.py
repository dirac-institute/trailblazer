import os

from django.test import TestCase
from moto import mock_secretsmanager
import boto3
import yaml


import trail.config as ConfigModule
from trail.config import Config, DbAuth, SiteConfig


TESTDIR = os.path.abspath(os.path.dirname(__file__))


class ConfigTestCase(TestCase):
    testConfigDir = os.path.join(TESTDIR, "config")

    def setUp(self):
        self.badConf = os.path.join(self.testConfigDir, "badPermissionConf.yaml")
        self.goodConf = os.path.join(self.testConfigDir, "conf.yaml")
        self.noExists = os.path.join(self.testConfigDir, "noexist.yaml")

    def tearDown(self):
        pass

    def testInstantiation(self):
        """Test various Config instantiation methods."""
        # Test 600 permissions
        with self.assertRaises(PermissionError):
            Config.fromYaml(self.badConf)

        # Test missing file
        with self.assertRaises(FileNotFoundError):
            Config.fromYaml(self.noExists)

        # Test that fromYaml and direct instantiation produce same result
        # Test it's possible to instantiate without errors, test env var and
        # global var default instantiations.
        try:
            conf1 = Config.fromYaml(self.goodConf)
        except Exception as e:
            self.fail(f"ConfigTestCase.testConfig conf1 failed with:\n{e}")

        with open(self.goodConf, 'r') as stream:
            confDict = yaml.safe_load(stream)
        try:
            conf2 = Config(confDict)
        except Exception as e:
            self.fail(f"ConfigTestCase.testConfig conf2 failed with:\n{e}")

        self.assertEqual(conf1, conf2)

        ConfigModule.CONF_FILE_PATH = self.goodConf
        try:
            conf3 = Config.fromYaml()
        except Exception as e:
            self.fail(f"ConfigTestCase.testConfig conf3 failed with:\n{e}")

        self.assertEqual(conf2, conf3)

        # Switch to a different conf file to verify overriding with env var
        # works as intended
        os.environ[ConfigModule.CONF_FILE_ENVVAR] = self.badConf
        with self.assertRaises(PermissionError):
            conf4 = Config.fromYaml()

    def testConfigKey(self):
        """Test only the correct config key is read."""
        Config.configKey = "noexists"
        with self.assertRaises(ValueError):
            Config.fromYaml(self.goodConf)

        # this is a bit silly, I think, because it doesn't test correctness?
        Config.configKey = "db"
        conf1 = Config.fromYaml(self.goodConf)
        conf2 = DbAuth.fromYaml(self.goodConf)
        self.assertEqual(conf1, conf2)

    def testAsDict(self):
        """Test Config.asDict() method."""
        with open(self.goodConf, 'r') as stream:
            confDict = yaml.safe_load(stream)

        conf = Config.fromYaml(self.goodConf)
        self.assertEqual(conf.asDict(), confDict)

        capitalizedSettings = {k.upper():v for k,v in confDict["settings"].items()}
        capitalizedDb = {k.upper():v for k,v in confDict["db"].items()}
        capitalizedDict = {k.upper():v for k,v in confDict.items()}
        capitalizedDict["SETTINGS"] = capitalizedSettings
        capitalizedDict["DB"] = capitalizedDb
        self.assertEqual(conf.asDict(capitalizeKeys=True), capitalizedDict)


class AwsSecretsTestCase(TestCase):
    testConfigDir = os.path.join(TESTDIR, "config")

    def setUp(self):
        self.goodConf = os.path.join(self.testConfigDir, "conf.yaml")
        self.awsSecretsConf = os.path.join(self.testConfigDir, "awsSecretsConf.yaml")

    @mock_secretsmanager
    def testSimpleAwsSecrets(self):
        """Test AWS Secrets Manager correctly instantiates Config."""
        smClient = boto3.client("secretsmanager", region_name="us-west-2")
        smClient.create_secret(Name="nonsense", SecretString="test-secret-key")

        conf = SiteConfig.fromYaml(self.goodConf, useAwsSecrets=True)

        self.assertEqual(conf.secret_key, "test-secret-key")

    @mock_secretsmanager
    def testMultiKeyedSecret(self):
        """Test multiple keys are correctly fetched from Secrets manager."""
        multiKeyedSecret = {
            "ENGINE": "postgresql",
            "NAME": "dbname",
            "USER": "dbuser",
            "PASSWORD": "dbpassword",
            "HOST": "dbhost.alala.com",
            "PORT": 5432,
        }
        smClient = boto3.client("secretsmanager", region_name="us-west-2")
        smClient.create_secret(Name="db-secret", SecretString=str(multiKeyedSecret))

        conf = DbAuth.fromYaml(self.awsSecretsConf, useAwsSecrets=True)
        self.assertEqual(conf.asDict(), multiKeyedSecret)

        # verify that the replaced key was not inserted
        with self.assertRaises(AttributeError):
            conf.secret_name



