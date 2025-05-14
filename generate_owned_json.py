import json
import requests
import os
import re
from thefuzz import fuzz

# URL of the original tonies JSON
TONIES_URL = 'https://raw.githubusercontent.com/toniebox-reverse-engineering/tonies-json/release/tonies.json'
# Path to your local NFC repo fork directory
NFC_REPO_PATH = 'origin_repo'
# Fuzzy matching threshold; adjust as necessary
FUZZY_THRESHOLD = 80

def fetch_tonies():
    """Download and return the JSON data from TONIES_URL."""
    response = requests.get(TONIES_URL)
    response.raise_for_status()
    return response.json()

def get_nfc_file_paths(nfc_repo_path):
    """
    Walk the NFC repository and return a list of relative file paths
    for all .nfc files.
    """
    file_paths = []
    for root, _, files in os.walk(nfc_repo_path):
        for file in files:
            if file.endswith('.nfc'):
                rel_path = os.path.relpath(os.path.join(root, file), nfc_repo_path)
                file_paths.append(rel_path)
    return file_paths

def replace_umlauts(text):
    """
    Replace German umlauts in the given text with their ASCII equivalents.
    """
    umlaut_map = {
        'ä': 'ae',
        'ö': 'oe',
        'ü': 'ue',
        'ß': 'ss'
    }
    for umlaut, replacement in umlaut_map.items():
        text = text.replace(umlaut, replacement)
    return text


def is_item_owned(series, episodes, language, nfc_paths, threshold=FUZZY_THRESHOLD):
    """
    Build a search string from series, episodes, and language then use fuzzy matching
    against each NFC file path.

    The language property is converted:
      - "de-de" becomes "german"
      - "fr-fr" becomes "french"
      - "en-gb"/"en-us" becomes "english"

    The function returns True if any NFC file path yields a fuzzy matching score above
    the threshold.
    """
    # Mapping of language codes to language names
    lang_mapping = {
        'de-de': 'german',
        'fr-fr': 'french',
        'en-gb': 'english',
        'en-us': 'english'
    }
    language_lower = language.lower().strip()
    language_name = lang_mapping.get(language_lower, "")

    search_term = f"{language_name}\\{series}\\{episodes}.nfc".lower().strip()
    for path in filter(lambda p: p.lower().startswith(f"{language_name}"), nfc_paths):
        path_parts = path.lower().split("\\")
        if len(path_parts) < 3:
            continue

        path_language, path_series, path_episodes = path_parts[0], path_parts[1], path_parts[2]
        path_term = f"{path_language}\\{path_series}\\{path_episodes}"

        score = fuzz.ratio(search_term, path_term)
        if score >= threshold:
            return True
    return False

def main():
    # Fetch the original tonies JSON.
    tonies_data = fetch_tonies()
    # Get all NFC file paths from the local NFC repository fork.
    nfc_paths = get_nfc_file_paths(NFC_REPO_PATH)

    filtered_items = []
    for item in tonies_data:
        model = str(item.get('model', '')).strip()
        # Exclude if model is empty or contains characters other than numbers and dash
        if not model or not re.fullmatch(r'[0-9-]+', model):
            continue
        # If the model does NOT contain a dash, it must start with a "1"
        if '-' not in model and not model.startswith('1'):
            continue
        # If the model does contain a dash, it must NOT start with a "09", "10", or "99"
        if '-' in model and (model.startswith('09') or model.startswith('10') or model.startswith('99')):
            continue

        category = str(item.get('category', '')).strip()
        # Exclude if category is empty or is creative-tonie
        if category == 'creative-tonie':
            continue

        series = replace_umlauts(str(item.get('series', '')).strip())
        episodes = replace_umlauts(str(item.get('episodes', '')).strip())
        language = str(item.get('language', '')).strip()

        # Add the "owned" flag based on fuzzy matching including language.
        item['owned'] = is_item_owned(series, episodes, language, nfc_paths)
        filtered_items.append(item)

    # Write the filtered items with the 'owned' property to a new JSON file.
    with open('tonies.json', 'w', encoding='utf-8') as f:
        json.dump(filtered_items, f, ensure_ascii=False, indent=2)

    print("Generated tonies.json with the 'owned' property for filtered items.")

if __name__ == '__main__':
    main()
