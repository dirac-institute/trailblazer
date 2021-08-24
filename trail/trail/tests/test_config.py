import unittest
import yaml
import sys
import os

from moto import mock_secretsmanager
from django.test import TestCase
import boto3

import trail.config as ConfigModule
from trail.config import get_secrets_filepath, Config, SecretsConfig


TESTDIR = os.path.abspath(os.path.dirname(__file__))


@unittest.skipIf(sys.platform == "win32", reason="Unable to consistently set file permissions on Windows.")
class ConfigTestCase(TestCase):
    testConfigDir = os.path.join(TESTDIR, "config")

    def setUp(self):
        self.badConf = os.path.join(self.testConfigDir, "badPermissionConf.yaml")
        self.goodConf = os.path.join(self.testConfigDir, "conf.yaml")
        os.chmod(self.goodConf, 0o600)
        self.noExists = os.path.join(self.testConfigDir, "noexist.yaml")

    def tearDown(self):
        pass

    def testInstantiation(self):
        """Test various Config instantiation methods."""
        # Test 600 permissions
        with self.assertRaises(PermissionError):
            SecretsConfig.fromYaml(self.badConf)

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
            conf3 = Config.fromYaml(get_secrets_filepath())
        except Exception as e:
            self.fail(f"ConfigTestCase.testConfig conf3 failed with:\n{e}")

        self.assertEqual(conf2, conf3)

        # Switch to a different conf file to verify overriding with env var
        # works as intended
        os.environ[ConfigModule.CONF_FILE_ENVVAR] = self.badConf
        with self.assertRaises(PermissionError):
            SecretsConfig.fromYaml(get_secrets_filepath())

    def testAsDict(self):
        """Test Config.asDict() method."""
        with open(self.goodConf, 'r') as stream:
            confDict = yaml.safe_load(stream)

        conf = Config.fromYaml(self.goodConf)
        self.assertEqual(conf.asDict(), confDict)

        capitalizedSettings = {k.upper(): v for k, v in confDict["django"].items()}
        capitalizedDb = {k.upper(): v for k, v in confDict["db"].items()}
        capitalizedDict = {k.upper(): v for k, v in confDict.items()}
        capitalizedDict["DJANGO"] = capitalizedSettings
        capitalizedDict["DB"] = capitalizedDb
        self.assertEqual(conf.asDict(capitalizeKeys=True), capitalizedDict)


@unittest.skipIf(sys.platform == "win32", reason="Unable to consistently set file permissions on Windows.")
class AwsSecretsTestCase(TestCase):
    testConfigDir = os.path.join(TESTDIR, "config")

    def setUp(self):
        self.goodConf = os.path.join(self.testConfigDir, "conf.yaml")
        os.chmod(self.goodConf, 0o600)
        self.awsSecretsConf = os.path.join(self.testConfigDir, "awsSecretsConf.yaml")
        os.chmod(self.awsSecretsConf, 0o600)

    @mock_secretsmanager
    def testSimpleAwsSecrets(self):
        """Test AWS Secrets Manager correctly instantiates Config."""
        smClient = boto3.client("secretsmanager", region_name="us-west-2")
        smClient.create_secret(Name="nonsense", SecretString="test-secret-key")

        conf = SecretsConfig.fromYaml(self.goodConf, useAwsSecrets=True)
        self.assertEqual(conf.django.secret_key, "test-secret-key")

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

        conf = SecretsConfig.fromYaml(self.awsSecretsConf, useAwsSecrets=True)
        self.assertEqual(conf.db.asDict(), multiKeyedSecret)

        # verify that the replaced key was not inserted
        with self.assertRaises(AttributeError):
            conf.secret_name
