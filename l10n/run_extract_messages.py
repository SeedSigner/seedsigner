import re
import subprocess
import sys
from pathlib import Path


POT_FILE_PATH = Path("l10n/messages.pot")


def strip_metadata(lines):
    # Removes lines starting with the POT-Creation-Date or Generated-By
    meta_re = re.compile(r'^"(POT-Creation-Date|Generated-By):')
    return [line for line in lines if not meta_re.match(line)]


def main():
    if not POT_FILE_PATH.exists():
        print(f"{POT_FILE_PATH} does not exist. Make sure that your local repo has fetched the `seedsigner-translations` submodule.")
        sys.exit(1)

    # keepends=True preserves newline chars so join writes the file back exactly.
    # This avoids unnecessary git diffs if different newline chars are used
    original = POT_FILE_PATH.read_text().splitlines(keepends=True)

    # This command updates messages.pot in place
    result = subprocess.run("python3 setup.py extract_messages", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running extract_messages:\n\n{result.stderr}")
        sys.exit(1)

    new = POT_FILE_PATH.read_text().splitlines(keepends=True)

    if strip_metadata(original) == strip_metadata(new):
        print("All strings are up to date.")
        # Restore original file if no changes
        POT_FILE_PATH.write_text("".join(original))
        sys.exit(0)

    else:
        print(
            "messages.pot was regenerated.\n"
            "Stage the update and re-run your commit:\n"
            "  git add l10n/messages.pot"
        )

if __name__ == "__main__":
    main()
