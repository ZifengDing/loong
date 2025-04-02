import os
import json
import sys
import subprocess

REQUIRED_FIELDS = {"question", "final_answer", "rationale", "metadata"}
REQUIRED_METADATA_FIELDS = {"license", "source", "domain"}
PERMISSIVE_LICENSES = {"MIT", "Apache-2.0", "CC BY 4.0", "CC-BY"}

def get_changed_seed_files():
    try:
        base_ref = os.environ.get('GITHUB_BASE_REF')
        if base_ref:
            # PR context
            cmd = f"git diff --name-only origin/{base_ref} HEAD"
        else:
            # Push to main
            cmd = "git diff --name-only HEAD~1 HEAD"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        files = result.stdout.strip().split('\n')
        return [f for f in files if f.startswith("data/") and f.endswith("seed.json")]
    except Exception as e:
        print(f"⚠️ Failed to get changed files: {e}")
        return []

def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def is_valid_license(license_str):
    return license_str in PERMISSIVE_LICENSES

def validate_entry(entry, idx, domain):
    errors = []
    if not isinstance(entry, dict):
        errors.append(f"[{idx}] Not a dictionary.")
        return errors

    missing = REQUIRED_FIELDS - entry.keys()
    if missing:
        errors.append(f"[{idx}] Missing required fields: {missing}")

    metadata = entry.get("metadata", {})
    if not isinstance(metadata, dict):
        errors.append(f"[{idx}] 'metadata' is not a dict.")
        return errors

    for field in REQUIRED_METADATA_FIELDS:
        if field not in metadata:
            errors.append(f"[{idx}] Missing metadata.{field}")

    license_val = metadata.get("license")
    if license_val and not is_valid_license(license_val):
        errors.append(f"[{idx}] Invalid license: {license_val}")

    entry_domain = metadata.get("domain")
    if entry_domain and entry_domain != domain:
        errors.append(f"[{idx}] Domain mismatch: expected '{domain}', got '{entry_domain}'")

    return errors

def infer_domain_from_path(path):
    parts = path.split(os.sep)
    if len(parts) >= 2:
        return parts[1]  # e.g., data/games/blackjack/seed.json → games
    return None

def validate_seed_file(path):
    errors = []
    try:
        data = load_json(path)
    except Exception as e:
        return [f"{path}: Invalid JSON - {e}"]

    if not isinstance(data, list):
        return [f"{path}: Must be a list of entries"]

    domain = infer_domain_from_path(path)
    if not domain:
        return [f"{path}: Couldn't infer domain from path"]

    for idx, entry in enumerate(data):
        errors.extend([f"{path} {e}" for e in validate_entry(entry, idx, domain)])
    return errors

def main():
    seed_files = get_changed_seed_files()
    if not seed_files:
        print("✅ No changed seed.json files found.")
        return

    all_errors = []
    for path in seed_files:
        print(f"🔍 Validating {path}...")
        all_errors.extend(validate_seed_file(path))

    if all_errors:
        print("🚨 Validation failed:")
        for e in all_errors:
            print(f"❌ {e}")
        sys.exit(1)
    else:
        print("✅ All seed files valid.")

if __name__ == "__main__":
    main()
