"""Explore the public NREL PVDAQ S3 bucket — listing only, no downloads.

Module 1 (Fleet Data Ingestion) needs real inverter generation data from
NREL PVDAQ, which is hosted as a public dataset on the AWS Open Data
Registry. The bucket layout is not documented here on purpose: this script
discovers it one level at a time so we build ingestion against what is
actually there rather than what we assumed.

The bucket is public and requires no AWS credentials. We pass an UNSIGNED
signature config so boto3 does not look for (or complain about the absence
of) credentials on the machine.

Usage:
    python pipeline/explore_bucket.py                 # lists "pvdaq/"
    python pipeline/explore_bucket.py pvdaq/2023/     # lists one level deeper

Deliberately does NOT download anything. Downloading is a separate step.
"""

import argparse
import sys

try:
    import boto3
    from botocore import UNSIGNED
    from botocore.client import Config
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    print("boto3 is not installed. Install it with:  pip install boto3")
    sys.exit(1)


BUCKET_NAME = "oedi-data-lake"
DEFAULT_PREFIX = "pvdaq/"
BYTES_PER_MB = 1024 * 1024

# One page of list_objects_v2 is enough to understand a folder's shape.
# Raise this only if a level turns out to be genuinely wide.
MAX_KEYS_PER_REQUEST = 1000


def build_anonymous_s3_client():
    """Return an S3 client that sends no credentials.

    UNSIGNED is what makes this work against a public bucket from a machine
    with no AWS profile configured.
    """
    return boto3.client("s3", config=Config(signature_version=UNSIGNED))


def normalise_prefix(prefix):
    """Ensure a non-empty prefix ends in "/" so the delimiter listing works.

    Without the trailing slash, S3 treats "pvdaq" as a name fragment and
    returns the parent level instead of the folder's contents.
    """
    if not prefix:
        return ""
    if prefix.endswith("/"):
        return prefix
    return prefix + "/"


def list_one_level(s3_client, prefix):
    """List folders and files directly under `prefix`, one level only.

    Delimiter="/" is what collapses everything below this level into
    CommonPrefixes, so we see folder names instead of every object in the
    tree.

    Returns (folder_prefixes, file_objects, is_truncated).
    """
    response = s3_client.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=prefix,
        Delimiter="/",
        MaxKeys=MAX_KEYS_PER_REQUEST,
    )

    folder_prefixes = [entry["Prefix"] for entry in response.get("CommonPrefixes", [])]
    file_objects = response.get("Contents", [])
    is_truncated = response.get("IsTruncated", False)

    # S3 returns the prefix itself as a zero-byte "folder marker" object in
    # some buckets. It is not a real file, so drop it.
    file_objects = [obj for obj in file_objects if obj["Key"] != prefix]

    return folder_prefixes, file_objects, is_truncated


def format_size_mb(size_in_bytes):
    """Format a byte count as MB, keeping small files visible rather than 0.00."""
    size_in_mb = size_in_bytes / BYTES_PER_MB
    if size_in_mb < 0.01:
        return "<0.01 MB"
    return "{:.2f} MB".format(size_in_mb)


def print_folders(folder_prefixes):
    print("FOLDERS ({}):".format(len(folder_prefixes)))
    if not folder_prefixes:
        print("  (none at this level)")
        return
    for folder_prefix in folder_prefixes:
        print("  {}".format(folder_prefix))


def print_files(file_objects):
    print("FILES ({}):".format(len(file_objects)))
    if not file_objects:
        print("  (none at this level)")
        return
    total_bytes = 0
    for file_object in file_objects:
        total_bytes += file_object["Size"]
        print("  {}  [{}]".format(file_object["Key"], format_size_mb(file_object["Size"])))
    print("  ---")
    print("  total at this level: {}".format(format_size_mb(total_bytes)))


def explore(prefix):
    """Print one level of the bucket. Returns a process exit code."""
    prefix = normalise_prefix(prefix)

    print("bucket : s3://{}".format(BUCKET_NAME))
    print("prefix : {!r}".format(prefix))
    print("mode   : listing only, nothing downloaded")
    print("-" * 70)

    try:
        s3_client = build_anonymous_s3_client()
        folder_prefixes, file_objects, is_truncated = list_one_level(s3_client, prefix)
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code", "Unknown")
        print("S3 refused the request (code: {}).".format(error_code))
        print("Check the bucket name and prefix are correct and publicly readable.")
        return 1
    except BotoCoreError as error:
        print("Could not reach S3: {}".format(error))
        print("Check the network connection, then retry.")
        return 1

    if not folder_prefixes and not file_objects:
        print("Nothing found under {!r}.".format(prefix))
        print("Either the prefix does not exist, or it is spelled differently.")
        print("Try a shallower prefix — e.g. '' to list the top of the bucket.")
        return 0

    print_folders(folder_prefixes)
    print("")
    print_files(file_objects)

    if is_truncated:
        print("")
        print("NOTE: results truncated at {} entries — this level has more.".format(MAX_KEYS_PER_REQUEST))

    return 0


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="List one level of the public NREL PVDAQ S3 bucket. Does not download.",
    )
    parser.add_argument(
        "prefix",
        nargs="?",
        default=DEFAULT_PREFIX,
        help='Prefix to list, e.g. "pvdaq/" (default) or "pvdaq/2023/".',
    )
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    return explore(arguments.prefix)


if __name__ == "__main__":
    sys.exit(main())
