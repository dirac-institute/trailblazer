import os


__all__ = ("getS3Client", "s3CheckFileExists", "bucketExists", "setAwsEnvCredentials",
           "unsetAwsEnvCredentials")


try:
    import boto3
except ImportError:
    boto3 = None

try:
    import botocore
except ImportError:
    botocore = None

from utils.uri import URI


def getS3Client():
    """Create a S3 client with AWS (default) or the specified endpoint

    Returns
    -------
    s3client : `botocore.client.S3`
        A client of the S3 service.

    Notes
    -----
    The endpoint URL is from the environment variable S3_ENDPOINT_URL.
    If none is specified, the default AWS one is used.
    """
    if boto3 is None:
        raise ModuleNotFoundError("Could not find boto3. "
                                  "Are you sure it is installed?")
    if botocore is None:
        raise ModuleNotFoundError("Could not find botocore. "
                                  "Are you sure it is installed?")

    endpoint = os.environ.get("S3_ENDPOINT_URL", None)
    if not endpoint:
        endpoint = None  # Handle ""

    config = botocore.config.Config(
        read_timeout=180,
        retries={
            'mode': 'adaptive',
            'max_attempts': 10
        }
    )

    return boto3.client("s3", endpoint_url=endpoint, config=config)


def s3CheckFileExists(path, bucket=None, client=None):
    """Returns (True, filesize) if file exists in the bucket and (False, -1) if
    the file is not found.

    Parameters
    ----------
    path : `str`
        Location containing the bucket name and filepath.
    bucket : `str`, optional
        Name of the bucket in which to look. If provided, path will be assumed
        to correspond to be relative to the given bucket.
    client : `boto3.client`, optional
        S3 Client object to query, if not supplied boto3 will try to resolve
        the credentials as in order described in its manual_.

    Returns
    -------
    exists : `bool`
        True if key exists, False otherwise.
    size : `int`
        Size of the key, if key exists, in bytes, otherwise -1

    Notes
    -----
    S3 Paths are sensitive to leading and trailing path separators.

    .. _manual: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/\
    configuration.html#configuring-credentials
    """
    if boto3 is None:
        raise ModuleNotFoundError("Could not find boto3. "
                                  "Are you sure it is installed?")

    if client is None:
        client = getS3Client()

    if isinstance(path, str):
        if bucket is not None:
            filepath = path
        else:
            uri = URI(path)
            bucket = uri.netloc
            filepath = uri.relativeToPathRoot
    elif isinstance(path, URI):
        bucket = path.netloc
        filepath = path.relativeToPathRoot

    try:
        obj = client.head_object(Bucket=bucket, Key=filepath)
        return (True, obj["ContentLength"])
    except client.exceptions.ClientError as err:
        # resource unreachable error means key does not exist
        if err.response["ResponseMetadata"]["HTTPStatusCode"] == 404:
            return (False, -1)
        # head_object returns 404 when object does not exist only when user has
        # s3:ListBucket permission. If list permission does not exist a 403 is
        # returned. In practical terms this generally means that the file does
        # not exist, but it could also mean user lacks s3:GetObject permission:
        # https://docs.aws.amazon.com/AmazonS3/latest/API/RESTObjectHEAD.html
        # I don't think its possible to discern which case is it with certainty
        if err.response["ResponseMetadata"]["HTTPStatusCode"] == 403:
            raise PermissionError("Forbidden HEAD operation error occured. "
                                  "Verify s3:ListBucket and s3:GetObject "
                                  "permissions are granted for your IAM user. ") from err
        raise


def bucketExists(bucketName, client=None):
    """Check if the S3 bucket with the given name actually exists.

    Parameters
    ----------
    bucketName : `str`
        Name of the S3 Bucket
    client : `boto3.client`, optional
        S3 Client object to query, if not supplied boto3 will try to resolve
        the credentials as in order described in its manual_.

    Returns
    -------
    exists : `bool`
        True if it exists, False if no Bucket with specified parameters is
        found.

    .. _manual: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/\
    configuration.html#configuring-credentials
    """
    if boto3 is None:
        raise ModuleNotFoundError("Could not find boto3. "
                                  "Are you sure it is installed?")

    if client is None:
        client = getS3Client()
    try:
        client.get_bucket_location(Bucket=bucketName)
        return True
    except client.exceptions.NoSuchBucket:
        return False


def setAwsEnvCredentials(accessKeyId='dummyAccessKeyId',
                         secretAccessKey="dummySecretAccessKey"):
    """Set AWS credentials environmental variables AWS_ACCESS_KEY_ID and
    AWS_SECRET_ACCESS_KEY.

    Parameters
    ----------
    accessKeyId : `str`
        Value given to AWS_ACCESS_KEY_ID environmental variable. Defaults to
        'dummyAccessKeyId'
    secretAccessKey : `str`
        Value given to AWS_SECRET_ACCESS_KEY environmental variable. Defaults
        to 'dummySecretAccessKey'

    Returns
    -------
    setEnvCredentials : `bool`
        True when environmental variables were set, False otherwise.

    Notes
    -----
    If either AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY are not set, both
    values are overwritten.
    """
    if "AWS_ACCESS_KEY_ID" not in os.environ or "AWS_SECRET_ACCESS_KEY" not in os.environ:
        os.environ["AWS_ACCESS_KEY_ID"] = accessKeyId
        os.environ["AWS_SECRET_ACCESS_KEY"] = secretAccessKey
        return True
    return False


def unsetAwsEnvCredentials():
    """Unsets AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environmental
    variables.
    """
    if "AWS_ACCESS_KEY_ID" in os.environ:
        del os.environ["AWS_ACCESS_KEY_ID"]
    if "AWS_SECRET_ACCESS_KEY" in os.environ:
        del os.environ["AWS_SECRET_ACCESS_KEY"]
