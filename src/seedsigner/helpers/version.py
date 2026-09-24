import json
import logging
import os
import traceback

from datetime import datetime, timezone

from seedsigner.models.settings import Settings
from seedsigner.models.singleton import Singleton


logger = logging.getLogger(__name__)



# Note: If this exception and its associated decorator end up being useful elsewhere, move
# them to a more general location (e.g. create a helpers/exceptions.py).
class NotAllowedInSeedSignerOS(Exception):
    pass


def not_allowed_in_seedsigner_os(func: callable):
    """ Simple decorator to enforce SeedSigner OS restrictions. """
    def wrapper_func(*args, **kwargs):
        if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
            raise NotAllowedInSeedSignerOS(f"Cannot run `{func.__name__}` in SeedSigner OS.")

        # Now run the target function and return its results
        return func(*args, **kwargs)
    return wrapper_func




class Version(Singleton):
    """
    Utility class to report the current version and the last edit time of the source code.

    Implemented as a Singleton for convenient access (no need to keep passing an instance
    around in the main code) and so that the version data is only determined once per
    runtime.

    SeedSigner OS lifecycle:
        * The SeedSigner OS build process runs the tools/write_versionfile.py script to
          generate version.json.
        * The version.json file is included in the SeedSigner OS image.

    The version data is fetched differently depending on the environment:

    In SeedSigner OS:
        * Version data is read exclusively from version.json at runtime.

    In the SeedSigner OS builder:
    - Note: the build process relies on `git` being installed so we leverage it here.
        * version_name:
            * read dynamically from `git` shell calls to retrieve, in order:
                * Current git branch name
                * Current git tag name
                * Current git short commit hash
        * version_fork:
            * the git repo owner parsed out of the remote url.
            * https://github.com/SeedSigner/seedsigner.git -> "SeedSigner"
            * Read dynamically from shell `git` call to check the remote "origin" URL.
        * short_commit_hash:
            * the commit hash for the current branch / tag / detached HEAD.
            * Read dynamically from shell `git` call.
        * version_timestamp:
            * the last git commit time for the current branch / tag / detached HEAD.
            * Read dynamically from shell `git` call.

    In local dev:
    - Similar process as for the SeedSigner OS builder, but with additional fallbacks and
      a different method for determining version_timestamp.
    - If a local version.json is present, it will be ignored; it may be out of date and
      could lead to confusion.
        * version_name:
            * `git` shell calls + directly parsing the .git/HEAD file and .git/refs/tags
              when necessary.
        * version_fork:
            * `git` shell call + parse the .git/config for the remote "origin" URL.
        * commit_hash:
            * Shell `git` call + parse the .git/HEAD file and
              .git/refs/heads/<branch_name> when necessary.
        * version_timestamp: determined by scanning the src/ directory for the most
          recently modified python file.

    In Github Actions CI:
        * version_name: read from GITHUB_REF_NAME env var.
        * version_fork: read from PR_AUTHOR custom CI env var or GITHUB_REPOSITORY_OWNER.
        * version_timestamp: Shell `git` call to get the last commit time for the current
          branch/tag/commit.
        * commit_hash: read from SOURCE_SHA custom CI env var or GITHUB_SHA.

    This class defines the limited methods that are meant to be publicly accessible
    across the SeedSigner codebase.

    The utility functions in `VersionUtils` were explicitly isolated because they should
    NOT be used elsewhere in the codebase.
    TODO: Should `VersionUtils` be an internal class within `Version` to further signal
    that it is not to be used externally?
    TODO: Also pull git log history and display it in its own View?
    """
    _version_name: str = None
    _version_fork: str = None
    _short_commit_hash: str = None
    _version_timestamp: datetime = None


    @classmethod
    def get_instance(cls):
        """ This is the only way to access the one and only instance. """
        if not cls._instance:
            # Instantiate the one and only Version instance
            version = cls.__new__(cls)
            cls._instance = version

            # Populate version data
            version._version_name = VersionUtils.get_version_name()
            version._version_fork = VersionUtils.get_version_fork()
            version._version_timestamp = VersionUtils.get_version_timestamp()
            version._short_commit_hash = VersionUtils.get_short_commit_hash()
        return cls._instance


    @classmethod
    def get_version_name(cls) -> str | None:
        return cls.get_instance()._version_name


    @classmethod
    def get_version_fork(cls) -> str | None:
        return cls.get_instance()._version_fork


    @classmethod
    def get_short_commit_hash(cls) -> str | None:
        return cls.get_instance()._short_commit_hash


    @classmethod
    def get_version_timestamp(cls) -> datetime | None:
        return cls.get_instance()._version_timestamp


    @classmethod
    def is_release_image(cls) -> bool:
        """
        Returns True if all of the following are true:
        * We're running in SeedSigner OS.
        * `version_fork` is the main "seedsigner" repo.
        * `version_name` corresponds to a "clean" semantic version tag.
            * e.g. "v0.8.5" but not "v0.8.5-rc1".
        """
        if Settings.HOSTNAME != Settings.SEEDSIGNER_OS:
            return False
        
        fork = cls.get_version_fork()
        if not fork or fork.lower() != "seedsigner":
            return False

        version = cls.get_version_name()
        # Even though our release tags in git do not include "v", at this point in the
        # code the "v" will already be prepended to `version_name` if it is a semantic
        # version tag. If "v" is prepended to future release tags, logic further up the
        # chain will already gracefully handle it.
        if not version or not version.startswith("v"):
            return False

        # Is it a clean semantic version?
        version = version[1:]  # strip the "v" prefix
        for part in version.split("."):
            if not part.isnumeric():
                return False

        return True


    @classmethod
    @not_allowed_in_seedsigner_os
    def override_data(cls, **kwargs):
        """
        Only used by the screenshot generator.
        """
        instance = cls.get_instance()
        if VersionUtils.VERSIONFILE_ATTR__NAME in kwargs:
            instance._version_name = kwargs[VersionUtils.VERSIONFILE_ATTR__NAME]
        if VersionUtils.VERSIONFILE_ATTR__FORK in kwargs:
            instance._version_fork = kwargs[VersionUtils.VERSIONFILE_ATTR__FORK]
        if VersionUtils.VERSIONFILE_ATTR__SHORT_COMMIT_HASH in kwargs:
            instance._short_commit_hash = kwargs[VersionUtils.VERSIONFILE_ATTR__SHORT_COMMIT_HASH]
        if VersionUtils.VERSIONFILE_ATTR__TIMESTAMP in kwargs:
            instance._version_timestamp = kwargs[VersionUtils.VERSIONFILE_ATTR__TIMESTAMP]


    @classmethod
    def to_dict(cls) -> dict:
        instance = cls.get_instance()
        return {
            VersionUtils.VERSIONFILE_ATTR__NAME: instance._version_name,
            VersionUtils.VERSIONFILE_ATTR__FORK: instance._version_fork,
            VersionUtils.VERSIONFILE_ATTR__SHORT_COMMIT_HASH: instance._short_commit_hash,
            VersionUtils.VERSIONFILE_ATTR__TIMESTAMP: instance._version_timestamp.isoformat() if instance._version_timestamp else None,
        }



class VersionUtils:
    """ *********************************************************************************
    Not meant to be used elsewhere in the SeedSigner codebase (aside from
    tools/write_versionfile.py).

    Methods are separated out here to a rather extreme degree in order to enable all the
    mocking that is required for testing.

    Summary of functions:
        * Top-level "get" calls that manage all the possible ways of getting the version
          data in an environment-aware manner (SeedSigner OS, local dev, Github Actions
          CI).
        * Reading data from the version.json file (SeedSigner OS).
        * Getting data from SeedSigner OS build env vars.
        * Detecting Github Actions CI environment and getting data from its env vars.
        * Parsing local filesystem .git/ files.
        * Making shell `git` calls.
        * One external http GET to github to get the most recent release tag.
    ********************************************************************************* """

    ENV_VAR__IS_SEEDSIGNER_OS_BUILDER = "SEEDSIGNER_OS_BUILDER"
    ENV_VAR__GITHUB_ACTIONS__IS_CI = "CI"
    ENV_VAR__GITHUB_ACTIONS__HEAD_REF = "GITHUB_HEAD_REF"
    ENV_VAR__GITHUB_ACTIONS__REF_NAME = "GITHUB_REF_NAME"
    ENV_VAR__GITHUB_ACTIONS__SOURCE_SHA = "SOURCE_SHA"
    ENV_VAR__GITHUB_ACTIONS__SHA = "GITHUB_SHA"
    ENV_VAR__GITHUB_ACTIONS__PR_AUTHOR = "PR_AUTHOR"
    ENV_VAR__GITHUB_ACTIONS__REPOSITORY_OWNER = "GITHUB_REPOSITORY_OWNER"
    DOT_GIT_DIR_NAME = ".git"  # defined to facilitate mocking in tests
    VERSIONFILE__FILENAME = "version.json"
    VERSIONFILE_ATTR__NAME = "name"
    VERSIONFILE_ATTR__FORK = "fork"
    VERSIONFILE_ATTR__SHORT_COMMIT_HASH = "short_commit_hash"
    VERSIONFILE_ATTR__TIMESTAMP = "timestamp"


    """ *************************************************************************************
    Top-level "get" calls. These are the only functions meant to be called externally.
    ************************************************************************************* """
    @classmethod
    def get_version_name(cls) -> str:
        """
            Will prefix the version name "v" if it looks like a semantic version.
        """
        if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
            # The SeedSigner OS build process generates the version.json file for the tag,
            # branch, or commit hash the image is targeting.
            version_name = VersionUtils._get_version_name_from_version_file()
            if version_name is None:
                # Shouldn't be possible. Raise an exception to alert testers before this
                # image goes out.
                raise Exception("Could not read the version from the version.json file.")

            # Note: the version.json file already contains any necessary pre-processing so
            # if we're on a semantic version tag, version_name will already be prefixed
            # with "v".
            return version_name

        elif VersionUtils.is_github_actions_ci():
            # In Github Actions CI, try to get the version name from env vars
            version_name = VersionUtils._get_version_name_from_github_actions_env_vars()
            if version_name is not None:
                return VersionUtils._prefix_version_name(version_name)
            else:
                raise Exception("Could not determine version from Github Actions env vars.")

        else:
            # In the SeedSigner OS builder we know that we'll have the `git` shell
            # commands available. We add extra fallbacks for local dev.
            for get_version_name_method in [
                VersionUtils._get_version_name_from_git_shell,
                VersionUtils._get_version_name_from_git_HEAD,
            ]:
                version_name = get_version_name_method()
                if version_name is not None:
                    return VersionUtils._prefix_version_name(version_name)

        # If we reach here, none of the methods worked
        # TODO: What do we want to do in this case?
        # Intentionally not marking this for translation; end users should never see it.
        return "version not detected"


    @classmethod
    def get_version_fork(cls) -> str | None:
        """
        Returns the fork owner or None if it cannot be determined.

        e.g. https://github.com/SeedSigner/seedsigner -> "SeedSigner"
        """
        if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
            # The SeedSigner OS build process generates the version.json file which will
            # already contain the fork name.
            return VersionUtils._get_version_fork_from_version_file()

        elif VersionUtils.is_github_actions_ci():
            # In Github Actions CI, try to get the fork name from env vars.
            return VersionUtils._get_version_fork_from_github_actions_env_vars()

        else:
            # In the SeedSigner OS builder we know that we'll have the `git` shell
            # commands available. We add extra fallbacks for local dev.
            for get_version_fork_method in [
                VersionUtils._get_version_fork_from_git_shell,
                VersionUtils._get_version_fork_from_git_config,
            ]:
                version_fork = get_version_fork_method()
                if version_fork is not None:
                    return version_fork
        return None


    @classmethod
    def get_short_commit_hash(cls) -> str | None:
        """
        Returns the short commit hash string.

        Will be None if the local dev system has no git state available or if it only has
        the .git/HEAD but is currently on a branch (not a tag or specific commit).
        """
        if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
            return VersionUtils._get_short_commit_hash_from_version_file()

        full_commit_hash = None
        if VersionUtils.is_github_actions_ci():
            # In Github Actions CI the "SHA" env var should always be available
            full_commit_hash = VersionUtils._get_full_commit_hash_from_github_actions_env_vars()

        else:
            # In the SeedSigner OS builder we know that we'll have the `git` shell
            # commands available. We add extra fallbacks for local dev.
            for get_full_commit_hash_method in [
                VersionUtils._get_full_commit_hash_from_git_shell,
                VersionUtils._get_full_commit_hash_from_git_HEAD,
            ]:
                full_commit_hash = get_full_commit_hash_method()
                if full_commit_hash is not None:
                    break

            if full_commit_hash is None:
                # `git` shell calls didn't work and HEAD might be on a branch, so dig
                # deeper into the .git files to look up the commit hash via the branch
                # name.
                branch_name, expect_full_commit_hash_to_be_none = VersionUtils._read_git_HEAD_file()
                if branch_name:
                    full_commit_hash = VersionUtils._get_full_commit_hash_from_git_refs_heads(branch_name)

        if full_commit_hash is not None:
            return full_commit_hash[:7]


    @classmethod
    def get_version_timestamp(cls) -> datetime:
        """
        Returns a datetime object representing the last edit time of the source code via
        the most recent git commit time (SeedSigner OS, as written in version.json) or
        the most recently modified python source file (local dev).
        """
        if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
            # The SeedSigner OS build process generates the version.json file which will
            # already contain the last edit time.
            version_timestamp = VersionUtils._get_version_timestamp_from_version_file()
            if version_timestamp is None:
                # Shouldn't be possible. Raise an exception to alert testers before this
                # image goes out.
                raise Exception("Could not read the version timestamp from the version.json file.")
            return datetime.fromisoformat(version_timestamp)

        elif VersionUtils.is_github_actions_ci():
            # In Github Actions CI `git` shell call should be available
            return VersionUtils._get_version_timestamp_from_git_shell()

        elif VersionUtils._is_seedsigner_os_builder_env():
            # In the SeedSigner OS builder we know that we'll have the `git` shell
            # commands available.
            # Note: This is the only piece of version data that behaves differently
            # between the SeedSigner OS builder and local dev.
            return VersionUtils._get_version_timestamp_from_git_shell()

        else:
            # In local dev we change our approach and instead use the last modified time
            # of the source python files.
            return VersionUtils._get_last_modified_timestamp_from_src_files()



    """ *************************************************************************************
    Misc internal utility functions.
    ************************************************************************************* """
    @classmethod
    def _prefix_version_name(cls, version_name: str) -> str:
        """
        Ensure version strings are prefixed with 'v' if they look like semantic
        versions. Only checks that the first part is numeric in order to be compatible
        with non-numeric minor versions (e.g. "0.8.5-rc1").
        """
        if not version_name.startswith("v") and version_name.count(".") >= 1 and version_name.split(".")[0].isnumeric():
            return f"v{version_name}"
        return version_name



    """ *************************************************************************************
    Reading data from the version.json file.
    ************************************************************************************* """
    @classmethod
    def _get_version_file_path(cls) -> str:
        # Have to back out of this file's location in the "helpers" dir to the main
        # "seedsigner" dir.
        return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", cls.VERSIONFILE__FILENAME))


    @classmethod
    def _read_version_file(cls) -> dict | None:
        """
        Attempts to read version.json and return its contents as a dict.
        """
        try:
            with open(cls._get_version_file_path(), "r") as f:
                return json.load(f)
        except FileNotFoundError as e:
            logger.debug(f"Ignoring {e}")
        except Exception as e:
            # Something unexpected happened. Flag it but keep going.
            logger.error(traceback.format_exc())


    @classmethod
    def _get_version_name_from_version_file(cls) -> str | None:
        """
        Attempts to read the version.json and return the version name.
        """
        version_data = cls._read_version_file()
        if version_data:
            return version_data.get(cls.VERSIONFILE_ATTR__NAME)


    @classmethod
    def _get_version_fork_from_version_file(cls) -> str | None:
        """
        Attempts to read the version.json and return the version fork name.
        """
        version_data = cls._read_version_file()
        if version_data:
            return version_data.get(cls.VERSIONFILE_ATTR__FORK)


    @classmethod
    def _get_short_commit_hash_from_version_file(cls) -> str | None:
        """
        Attempts to read the version.json and return the version commit hash.
        """
        version_data = cls._read_version_file()
        if version_data:
            return version_data.get(cls.VERSIONFILE_ATTR__SHORT_COMMIT_HASH)


    @classmethod
    def _get_version_timestamp_from_version_file(cls) -> str | None:
        """
        Attempts to read the version.json and return the version timestamp.
        """
        version_data = cls._read_version_file()
        if version_data:
            return version_data.get(cls.VERSIONFILE_ATTR__TIMESTAMP)



    """ *************************************************************************************
    Utilities used in the SeedSigner OS build environment and writing the version.json file.
    ************************************************************************************* """
    @classmethod
    def _is_seedsigner_os_builder_env(cls) -> bool:
        """
        The `ENV_VAR__IS_SEEDSIGNER_OS_BUILDER` env var is set during the SeedSigner OS
        build process.
        """
        return os.getenv(cls.ENV_VAR__IS_SEEDSIGNER_OS_BUILDER) is not None



    """ *************************************************************************************
    Getting data from Github Actions CI env vars.
    ************************************************************************************* """
    @classmethod
    def is_github_actions_ci(cls) -> bool:
        return os.getenv(cls.ENV_VAR__GITHUB_ACTIONS__IS_CI) == "true"


    @classmethod
    def _get_version_name_from_github_actions_env_vars(cls) -> str | None:
        """
        HEAD_REF: head ref or source branch. But only present for PRs.
        REF_NAME: branch or tag name. But it is "<pr_number>/merge" for unmerged PRs (not
        what we want)
        SOURCE_SHA is the full commit hash of the commit that triggered the workflow (if
        it's a PR).
        SHA is the full commit hash; not expecting to ever need this fallback.
        """
        for env_var in [
            cls.ENV_VAR__GITHUB_ACTIONS__HEAD_REF,
            cls.ENV_VAR__GITHUB_ACTIONS__REF_NAME,
            cls.ENV_VAR__GITHUB_ACTIONS__SOURCE_SHA,
            cls.ENV_VAR__GITHUB_ACTIONS__SHA
        ]:
            version_name = os.getenv(env_var)
            if version_name:
                if env_var in [cls.ENV_VAR__GITHUB_ACTIONS__SOURCE_SHA, cls.ENV_VAR__GITHUB_ACTIONS__SHA]:
                    # Return the short version
                    version_name = version_name[:7]
                return version_name


    @classmethod
    def _get_version_fork_from_github_actions_env_vars(cls) -> str | None:
        """
        PR_AUTHOR: Set by the .github/workflows/tests.yml workflow. Should be the PR author.
        REPOSITORY_OWNER: the repo owner, usually the main "SeedSigner" org.
        """
        for env_var in [
            cls.ENV_VAR__GITHUB_ACTIONS__PR_AUTHOR,
            cls.ENV_VAR__GITHUB_ACTIONS__REPOSITORY_OWNER
        ]:
            fork_name = os.getenv(env_var)
            if fork_name:
                return fork_name


    @classmethod
    def _get_full_commit_hash_from_github_actions_env_vars(cls) -> str | None:
        for env_var in [
            cls.ENV_VAR__GITHUB_ACTIONS__SOURCE_SHA,
            cls.ENV_VAR__GITHUB_ACTIONS__SHA
        ]:
            commit_hash = os.getenv(env_var)
            if commit_hash:
                return commit_hash



    """ *************************************************************************************
    Get data via shell `git` commands.

    These calls shouldn't be dangerous, but we definitely don't want them being run in
    SeedSigner OS regardless so we apply the decorator restriction.
    ************************************************************************************* """
    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_branch_name_from_git_shell(cls) -> str | None:
        branch_name = os.popen("git branch --show-current 2> /dev/null").read()
        return branch_name.strip() if branch_name else None


    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_tag_name_from_git_shell(cls) -> str | None:
        # Only return a value if the current commit exactly corresponds with a tag.
        # (`--points-at` defaults to the current HEAD)
        tag_name = os.popen(f"git tag --points-at 2> /dev/null").read()
        return tag_name.strip() if tag_name else None


    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_full_commit_hash_from_git_shell(cls) -> str | None:
        """
        Attempts to get the current full commit hash via shell `git` commands.
        """
        commit_hash = os.popen("git rev-parse HEAD").read()
        return commit_hash.strip() if commit_hash else None


    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_short_commit_hash_from_git_shell(cls) -> str | None:
        """
        Attempts to get the current short commit hash via shell `git` commands.
        """
        commit_hash = cls._get_full_commit_hash_from_git_shell()
        return commit_hash[:7] if commit_hash else None


    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_version_name_from_git_shell(cls) -> str | None:
        """
        Attempts to get the version name via shell `git` commands.

        Note: If we have to fall back to the commit hash, we use the short version.
        """
        return (
            cls._get_branch_name_from_git_shell() or
            cls._get_tag_name_from_git_shell() or
            cls._get_short_commit_hash_from_git_shell()
        )


    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_version_fork_from_git_shell(cls) -> str | None:
        """
        Attempts to get the fork owner name via shell `git` commands.
        """
        # We expect to at least have a remote named "origin"
        remote_url = os.popen("git remote get-url origin 2> /dev/null").read().strip()
        return cls._parse_git_remote_url(remote_url) if remote_url else None


    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_version_timestamp_from_git_shell(cls) -> datetime | None:
        version_timestamp = os.popen("git log -1 --format=%cI").read().strip()
        if version_timestamp:
            if version_timestamp.endswith("Z"):
                # Git outputs UTC time with a "Z" suffix; datetime.fromisoformat()
                # doesn't like the "Z" so we replace it with "+00:00"
                # TODO: Python 3.11+ has fromisoformat() support for "Z" suffixes so this
                # can be removed once we drop python 3.10 support.
                version_timestamp = version_timestamp.replace("Z", "+00:00")

            # Parse the timestamp, ensure that it's in UTC, and omit tz info
            return datetime.fromisoformat(version_timestamp).astimezone(timezone.utc).replace(tzinfo=None)



    """ *************************************************************************************
    Reading directly from local .git/ or src/ files.

    These operations aren't dangerous but aren't necessary when we're running in
    SeedSigner OS, so we apply the decorator restriction here.
    ************************************************************************************* """
    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_dot_git_dir(cls) -> str:
        # If it exists, the .git dir will be in the project root
        path = os.path.dirname(os.path.abspath(__file__))

        # Have to back out of this file's location in "helpers" and "seedsigner" and "src" dirs
        project_root = os.path.join(path, "..", "..", "..")

        return os.path.normpath(os.path.join(project_root, cls.DOT_GIT_DIR_NAME))


    @classmethod
    @not_allowed_in_seedsigner_os
    def _read_git_HEAD_file(cls) -> tuple[str | None, str | None]:
        """
        Reads the .git/HEAD file and returns a tuple of (branch_name, full_commit_hash) where
        only one will have a value.
        
        If there is no .git/HEAD file detected, both values will be None.
        """
        git_HEAD_path = os.path.join(cls._get_dot_git_dir(), "HEAD")

        branch_name = None
        full_commit_hash = None
        try:
            with open(git_HEAD_path, "r") as f:
                git_ref = f.read().strip()
                if git_ref.startswith("ref:"):
                    # HEAD format: "ref: refs/heads/some_branch_name"
                    branch_name = git_ref.split("/")[-1]
                else:
                    # If we're on a detached HEAD, the contents will just be the current
                    # full commit hash.
                    full_commit_hash = git_ref
        except FileNotFoundError as e:
            logger.debug(f"Ignoring {e}")
        except Exception as e:
            # Something unexpected happened. Flag it but keep going.
            logger.error(traceback.format_exc())
        return (branch_name, full_commit_hash)


    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_matching_tag_from_git_refs_tags(cls, commit_hash: str) -> str | None:
        """
        Checks the .git/refs/tags dir for a tag that matches the provided commit hash.
        """
        try:
            git_refs_tags_dir = os.path.join(cls._get_dot_git_dir(), "refs", "tags")
            for tag_filename in os.listdir(git_refs_tags_dir):
                tag_path = os.path.join(git_refs_tags_dir, tag_filename)
                with open(tag_path, "r") as tag_file:
                    # Tag files just contain their associated commit hash
                    tag_commit_hash = tag_file.read().strip()
                    if tag_commit_hash == commit_hash:
                        # Filename is the tag name
                        return tag_filename
        except FileNotFoundError as e:
            logger.debug(f"Ignoring {e}")
        except Exception as e:
            # Something unexpected happened. Flag it but keep going.
            logger.error(traceback.format_exc())


    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_version_name_from_git_HEAD(cls) -> str | None:
        """
        Reads the .git/HEAD file and, depending on the local dev git state, returns
        either the branch name, tag name, or short commit hash.
        """
        branch_name, commit_hash = VersionUtils._read_git_HEAD_file()
        if branch_name:
            return branch_name
        elif commit_hash:
            # See if this commit_hash matches a tag
            matching_tag = VersionUtils._get_matching_tag_from_git_refs_tags(commit_hash)
            if matching_tag:
                return matching_tag
            else:
                return commit_hash[:7]  # short commit hash


    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_full_commit_hash_from_git_HEAD(cls) -> str | None:
        """
        Reads the .git/HEAD file and, depending on the local dev git state, returns
        the full commit hash. Will only return a value if HEAD is detached (on a tag or
        on a specific commit).
        """
        branch_name, commit_hash = VersionUtils._read_git_HEAD_file()
        return commit_hash


    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_full_commit_hash_from_git_refs_heads(cls, branch_name: str) -> str | None:
        """
        When HEAD is on a branch, it doesn't tell us the commit hash directly. So we have
        to look it up here in .git/refs/heads/<branch_name>.
        """
        try:
            git_ref_path = os.path.join(cls._get_dot_git_dir(), "refs", "heads", branch_name)
            with open(git_ref_path, "r") as f:
                commit_hash = f.read().strip()
                return commit_hash
        except FileNotFoundError as e:
            logger.debug(f"Ignoring {e}")
        except Exception as e:
            # Something unexpected happened. Flag it but keep going.
            logger.error(traceback.format_exc())


    @classmethod
    def _parse_git_remote_url(cls, remote_url: str) -> str | None:
        """
        Parses a git remote URL to extract the fork owner name.

        Formats:
            * https://github.com/repo_owner/repo_name.git
            * git@github.com:repo_owner/repo_name.git
        """
        if not remote_url:
            return None
        if remote_url.startswith("https"):
            parts = remote_url.rsplit("/", 2)
            return parts[-2]
        elif remote_url.startswith("git@"):
            parts = remote_url.split(":")
            owner_repo = parts[1]  # repo_owner/repo_name.git
            return owner_repo.split("/")[0]


    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_version_fork_from_git_config(cls) -> str | None:
        """
        Attempts to read the .git/config file to determine the remote "origin" URL
        and extract the fork owner name from it.

        Format:
            [some_section]
                    some_key = some_value
            [remote "origin"]
                    url = git@github.com:SeedSigner/seedsigner.git
                    fetch = +refs/heads/*:refs/remotes/origin/*
            [next_section]
                    ...
        """
        try:
            git_config_path = os.path.join(cls._get_dot_git_dir(), "config")
            with open(git_config_path, "r") as f:
                lines = f.readlines()
                in_origin_section = False
                for line in lines:
                    line = line.strip()
                    if line.startswith("[remote \"origin\"]"):
                        # Next lines fetched will be the ones we care about
                        in_origin_section = True
                    elif in_origin_section and line.startswith("url ="):
                        # Found our "origin" url
                        remote_url = line.split("=", 1)[1].strip()
                        return cls._parse_git_remote_url(remote_url)
                    elif in_origin_section and line.startswith("["):
                        # We reached the next section without finding the url
                        raise Exception("Didn't find 'url' entry in 'origin' section of .git/config")
        except FileNotFoundError as e:
            logger.debug(f"Ignoring {e}")
        except Exception as e:
            # Something unexpected happened. Flag it but keep going.
            logger.error(traceback.format_exc())


    @classmethod
    @not_allowed_in_seedsigner_os
    def _get_last_modified_timestamp_from_src_files(cls) -> datetime | None:
        """
        Recursively scan the src/ directory for the most recent python file edit time.
        """
        try:
            path = os.path.dirname(os.path.abspath(__file__))

            # Have to back out of "helpers" and "seedsigner" dirs
            src_path = os.path.join(path, "..", "..")

            last_modified = 0.0
            num_files = 0
            for dirpath, dirnames, filenames in os.walk(src_path):
                if "__pycache__" in dirpath:
                    continue
                for filename in filenames:
                    if filename.endswith(".py"):
                        num_files += 1
                        filepath = os.path.join(dirpath, filename)

                        # getmtime returns the file's last modified time
                        file_mtime = os.path.getmtime(filepath)
                        last_modified = max(file_mtime, last_modified)
            if num_files == 0:
                # Shouldn't be possible
                raise Exception("No python source files found in src/ directory")

            return datetime.fromtimestamp(last_modified).astimezone(timezone.utc).replace(tzinfo=None)

        except Exception as e:
            # Catch and log any unexpected errors but this isn't a mission-critical
            # function so return gracefully.
            logger.error(traceback.format_exc())



    """ *************************************************************************************
    External http GET call to github.
    ************************************************************************************* """
    @classmethod
    @not_allowed_in_seedsigner_os
    def _fetch_latest_seedsigner_release_tag(cls) -> tuple[str, datetime] | tuple[None, None]:
        """
        Fetches the latest release version from the SeedSigner github repo via the
        github API. Then attempts to resolve the tag name locally to get its associated
        commit timestamp. If local git data is not available, falls back to using the
        release published_at time from the API.

        This is only used by the screenshot renderer.
        """
        import urllib.request
        from http.client import HTTPResponse

        try:
            """
            Excerpted example response from the github API:
                {
                    "url": "https://api.github.com/repos/SeedSigner/seedsigner/releases/228915183",
                    "tag_name": "0.8.6",
                    "prerelease": false,
                    "created_at": "2025-06-22T01:38:41Z",
                    "updated_at": "2025-06-30T20:49:22Z",
                    "published_at": "2025-06-30T20:45:05Z"
                }
            """
            req = urllib.request.Request(
                "https://api.github.com/repos/SeedSigner/seedsigner/releases/latest"
            )
            response: HTTPResponse = urllib.request.urlopen(req, timeout=5)
            if response.status == 200:
                release_data = json.loads(response.read().decode('utf-8'))
                version_name = release_data.get("tag_name")

                # Try to find the commit timestamp for this tag from local git data
                version_timestamp = os.popen(f"git show {version_name} --format=%cI").read().strip()
                if not version_timestamp:
                    # Fallback: use the release published_at time from the API
                    version_timestamp = release_data.get("published_at").replace("Z", "+00:00")
                version_timestamp = datetime.fromisoformat(version_timestamp).astimezone(timezone.utc).replace(tzinfo=None)
                return (VersionUtils._prefix_version_name(version_name), version_timestamp)
            else:
                logger.error(f"GitHub API returned status code {response.status}: {response}")
                return (None, None)
        except Exception as e:
            logger.error(f"Error fetching latest release version:\n{traceback.format_exc()}")
            return (None, None)