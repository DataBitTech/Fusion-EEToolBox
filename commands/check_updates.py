import os
import json
import urllib.request
import re


def get_current_version() -> list[int]:
    """Reads the current version from the ElectronicsExtendedToolBox.manifest file and returns it as a list of integers.

    The manifest file is expected to contain a version string in the format "major.minor.patch.",
    which is then converted to a list of integers [major, minor, patch].

    Returns:
        list[int]: A list containing the major, minor, and patch version numbers as integers.
    """
    manifest_path = os.path.join(os.path.dirname(__file__), '..', 'ElectronicsExtendedToolBox.manifest')
    try:
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
            version_string = manifest_data.get('version', '0.0.0')
            # Split the version string into parts and convert to integers
            version_parts = version_string.split('.')
            return [int(part) for part in version_parts]
    except Exception as e:
        return [0, 0, 0, 0]


def get_latest_version_from_autodesk_marketplace() -> list[int]:
    """Fetches the latest version number from the Autodesk Marketplace page.

    Returns:
        tuple[int]: A tuple containing the major, minor, sub and patch version numbers.
    """
    url = "https://marketplace.autodesk.com/apps/1ab36649-512f-4797-9bdc-68179270dac9?priceId=85abea3a-13a8-444f-a41c-9bd409506c40"
    version_not_found = [0, 0, 0, 0]
    try:
        with urllib.request.urlopen(url) as response:
            html = response.read().decode('utf-8')
            # Remove everything before the first match of the specific string
            match = re.search(r'1ab36649-512f-4797-9bdc-68179270dac9', html)
            if match:
                html = html[match.start():]
            else:
                return version_not_found

            # Look for version pattern in the remaining HTML
            version_pattern = r'"version":"(\d+\.\d+\.\d+(?:\.\d+)?)'
            version_match = re.search(version_pattern, html)
            if version_match:
                version_string = version_match.group(1)
                # Split version string into components
                version_parts = version_string.split('.')
                return [int(part) for part in version_parts]
            else:
                return version_not_found
    except Exception as e:
        return version_not_found


def compare_versions(current, latest) -> bool:
    """Compares the current version with the latest version and returns True if the latest version is greater.

    Args:
        current (list[int]): The current version as a list of integers [major, minor, patch, sub].
        latest (list[int]): The latest version as a list of integers [major, minor, patch, sub].

    Returns:
        bool: True if the latest version is greater than the current version, False otherwise.
    """
    # Pad lists to same length with zeros
    max_len = max(len(current), len(latest))
    current = current + [0] * (max_len - len(current))
    latest = latest + [0] * (max_len - len(latest))

    # Compare lists element by element
    for c, l in zip(current, latest):
        if l > c:
            return True
        elif c > l:
            return False
    return False  # They are equal


# only for testing
def main():
    print("Checking for updates..")
    current = get_current_version()
    print(f"Current version: {current}")
    
    latest = get_latest_version_from_autodesk_marketplace()
    if latest:
        print(f"Latest version: {latest}")
        if compare_versions(current, latest):
            print(f"A new version ({latest}) is available! Please update.")
        else:
            print("You are up to date.")
    else:
        print("Could not determine the latest version.")

if __name__ == "__main__":
    main()
