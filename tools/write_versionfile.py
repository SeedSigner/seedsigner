import json
import os

from seedsigner.helpers.version import Version, VersionUtils


"""
CLI utility to extract the current version data and write to
`src/seedsigner/version.json`. Primarily used by the SeedSigner OS build process.

Notes:
    * The SeedSigner OS build environment already relies on `git` being installed.
    * This script can also be run in local dev but note slight difference in how
      version_timestamp is gathered.
    * Tries to pull current version status via `git` shell commands, but has fallbacks
      to directly parse .git/ files.

Version data:
    * version_name: Retrieves the current git status by checking, in order:
        * Current git branch name
        * Current git tag name
        * Current git commit hash

    * version_fork:
        * The current repo owner.

    * short_commit_hash:
        * Current git short commit hash.

    * version_timestamp:
        * SeedSigner OS builder: Pulls last git commit time for the checked out
          branch/tag/commit.
        * Local dev: Scans the source python files for the most recent modified time.

"""
if __name__ == "__main__":
    # As soon as `Version` is instantiated, it will gather all the version data
    # according to the logic in `VersionUtils`.
    version_info = Version.get_instance().to_dict()

    # Write the version.json file.
    version_file_path = VersionUtils._get_version_file_path()
    with open(version_file_path, "w") as f:
        json.dump(version_info, f, indent=4)

    print(f"Wrote version info to: {version_file_path}")
    print(json.dumps(version_info, indent=4))
