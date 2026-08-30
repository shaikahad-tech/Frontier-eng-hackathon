"""Patch script to update repos.py with 25-repo support.

Run this once to update repos.py in-place:
    python src/phase5/patch_repos.py
"""
import os

REPOS_PY = os.path.join(os.path.dirname(__file__), "repos.py")

PATCHES = [
    # 1. Add repos_extended import after adversarial import
    (
        "    generate_repo_11, generate_repo_14, generate_repo_15,\n)\n\n\n# Repository generators registry",
        "    generate_repo_11, generate_repo_14, generate_repo_15,\n)\n\n# Import extended repo generators (repos 16-25)\nfrom src.phase5.repos_extended import (\n    generate_repo_16, generate_repo_17, generate_repo_18, generate_repo_19,\n    generate_repo_20, generate_repo_21, generate_repo_22, generate_repo_23,\n    generate_repo_24, generate_repo_25,\n)\n\n\n# Repository generators registry",
    ),
    # 2. Add repos 16-25 to REPO_GENERATORS
    (
        '    "repo_13": generate_repo_13, "repo_14": generate_repo_14, "repo_15": generate_repo_15,\n}',
        '    "repo_13": generate_repo_13, "repo_14": generate_repo_14, "repo_15": generate_repo_15,\n    "repo_16": generate_repo_16, "repo_17": generate_repo_17, "repo_18": generate_repo_18,\n    "repo_19": generate_repo_19, "repo_20": generate_repo_20, "repo_21": generate_repo_21,\n    "repo_22": generate_repo_22, "repo_23": generate_repo_23, "repo_24": generate_repo_24,\n    "repo_25": generate_repo_25,\n}',
    ),
    # 3. Fix repo_01's _git_init to not overwrite files with "initial"
    (
        '        {"files": {"src/dataprocessor/__init__.py": "", "src/dataprocessor/pipeline.py": "initial"}, "message": "Add core module"},\n        {"files": {"tests/test_pipeline.py": "initial"}, "message": "Add tests"},',
        '        {"files": {"src/dataprocessor/__init__.py": open(os.path.join(repo_path, "src/dataprocessor/__init__.py")).read(),\n                   "src/dataprocessor/pipeline.py": open(os.path.join(repo_path, "src/dataprocessor/pipeline.py")).read()}, "message": "Add core module"},\n        {"files": {"tests/test_pipeline.py": open(os.path.join(repo_path, "tests/test_pipeline.py")).read()}, "message": "Add tests"},',
    ),
]


def apply_patches():
    with open(REPOS_PY, "r") as f:
        content = f.read()

    for i, (old, new) in enumerate(PATCHES):
        if old in content:
            content = content.replace(old, new)
            print(f"Patch {i+1} applied")
        elif new in content:
            print(f"Patch {i+1} already applied")
        else:
            print(f"Patch {i+1} could not be applied (pattern not found)")

    with open(REPOS_PY, "w") as f:
        f.write(content)

    # Verify
    assert "repos_extended" in content, "repos_extended import missing"
    assert "repo_25" in content, "repo_25 missing"
    print(f"\nrepos.py updated: {len(content)} chars")
    print("Verification passed: repos_extended import and repo_25 present")


if __name__ == "__main__":
    apply_patches()
