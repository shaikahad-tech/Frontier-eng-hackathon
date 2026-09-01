#!/usr/bin/env python3
"""Patch script v2 — applies ALL fixes to orchestrator.py, specialists.py, verification.py.

Run after cloning the repo:
    python src/phase4/patch_v2.py
"""
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))


def patch_orchestrator():
    """Fix VERIFICATION_WEIGHTS, test_count field, confidence formula, add calibration."""
    path = os.path.join(BASE, "orchestrator.py")
    with open(path) as f:
        v = f.read()

    # Fix VERIFICATION_WEIGHTS (use regex for robustness)
    v = re.sub(r'"PARTIALLY_VERIFIED":\s*0\.75', '"PARTIALLY_VERIFIED": 0.9', v)
    v = re.sub(r'"UNKNOWN":\s*0\.5([,\s])', '"UNKNOWN": 0.95\\1', v)
    v = re.sub(r'"UNVERIFIED":\s*0\.25', '"UNVERIFIED": 0.7', v)
    v = re.sub(r'"CONTRADICTED":\s*0\.0.*', '"CONTRADICTED": 0.3,  # Heavily penalized but not fully suppressed', v)

    # Fix test_count field name in hard gate (use regex for robustness)
    v = re.sub(
        r'if not testing_raw\.get\("has_tests"\)',
        'test_file_count = testing_raw.get("test_file_count", 0)\n        test_function_count = testing_raw.get("test_function_count", 0)\n        has_tests = test_file_count > 0 or test_function_count > 0\n        if not has_tests:', v)

    # Fix confidence formula (use regex for robustness)
    v = re.sub(r'0\.5 \+ 0\.5 \* verify_metrics', '0.7 + 0.3 * verify_metrics', v)
    v = re.sub(r'adjusted_confidence = avg_confidence \* 0\.5$',
               'adjusted_confidence = avg_confidence * 0.7', v, flags=re.MULTILINE)

    # Add calibration after gated_score (check if not already added)
    if '_calibrate' not in v:
        old = '        final_score = weighted_sum / total_weight if total_weight > 0 else 0\n        gated_score, gate_reasons = self._apply_hard_gates(final_score, agent_results, evidence)'
        new = old + '''

        # Calibration: stretch scores to use full 0-100 range
        def _calibrate(raw):
            if raw < 20: return raw * 0.5
            elif raw < 40: return 10 + (raw - 20) * 1.25
            elif raw < 55: return 35 + (raw - 40) * 1.33
            elif raw < 70: return 55 + (raw - 55) * 1.33
            elif raw < 85: return 75 + (raw - 70) * 1.0
            else: return min(100, 90 + (raw - 85) * 0.67)
        gated_score = _calibrate(gated_score)'''
        v = v.replace(old, new)

    with open(path, "w") as f:
        f.write(v)
    print(f"orchestrator.py patched ({len(v)} chars)")


def patch_specialists():
    """Fix analyzer ID names and test field names in specialists.py."""
    path = os.path.join(BASE, "specialists.py")
    with open(path) as f:
        s = f.read()

    # Fix analyzer IDs to match Phase 2 output
    s = s.replace('"build_packaging"', '"build"')
    s = s.replace('"git_maturity"', '"git"')
    s = s.replace('"release_versioning"', '"release"')
    s = s.replace('"security_sast"', '"security"')

    with open(path, "w") as f:
        f.write(s)
    print(f"specialists.py patched ({len(s)} chars)")


def patch_verification():
    """Fix analyzer IDs and field name mismatches in verification.py."""
    path = os.path.join(BASE, "verification.py")
    with open(path) as f:
        v = f.read()

    # Fix analyzer IDs
    v = v.replace('get_findings("security_sast")', 'get_findings("security")')
    v = v.replace('get_raw_data("security_sast")', 'get_raw_data("security")')
    v = v.replace('get_raw_data("git_maturity")', 'get_raw_data("git")')
    v = v.replace('get_raw_data("release_versioning")', 'get_raw_data("release")')
    v = v.replace('get_raw_data("build_packaging")', 'get_raw_data("build")')
    v = v.replace('security_sast ran:', 'security ran:')
    v = v.replace('security_sast: 0', 'security: 0')
    v = v.replace('git_maturity:', 'git:')
    v = v.replace('release_versioning:', 'release:')

    # Fix _verify_documentation
    v = v.replace(
        'has_readme = doc_raw.get("has_readme", False)\n            readme_size = doc_raw.get("readme_size", 0)',
        'readme_info = doc_raw.get("readme", {})\n            if isinstance(readme_info, dict):\n                has_readme = readme_info.get("found", False)\n                readme_size = readme_info.get("length_chars", 0)\n            else:\n                has_readme = False\n                readme_size = 0'
    )

    # Fix _verify_git_activity
    v = v.replace(
        'commit_count = git_raw.get("commit_count", 0)',
        'commit_count = git_raw.get("total_commits", git_raw.get("commit_count", 0))'
    )

    # Fix _verify_test_count to use correct field names
    v = v.replace(
        'has_tests = testing_raw.get("has_tests", False)\n            test_count = testing_raw.get("test_count", 0)',
        'test_file_count = testing_raw.get("test_file_count", 0)\n            test_function_count = testing_raw.get("test_function_count", 0)\n            has_tests = test_file_count > 0 or test_function_count > 0'
    )
    v = v.replace(
        'supporting.append(f"testing: {test_count} tests detected")',
        'supporting.append(f"testing: {test_function_count} test functions in {test_file_count} files")'
    )

    # Fix _verify_test_pass to use correct field names
    v = v.replace(
        'if testing_raw and testing_raw.get("has_tests"):',
        'if testing_raw and (testing_raw.get("test_file_count", 0) > 0 or testing_raw.get("test_function_count", 0) > 0):'
    )

    # Replace _verify_structure entirely
    lines = v.split('\n')
    start = end = None
    for i, line in enumerate(lines):
        if "def _verify_structure" in line:
            start = i
        elif start is not None and i > start and line.startswith("    def "):
            end = i
            break
    if start and end:
        new_method = '''    def _verify_structure(self, finding, supporting, contradicting):
        struct_raw = self.evidence.get_raw_data("structure")
        if struct_raw:
            struct_score = struct_raw.get("score", 0)
            has_cyclic = len(struct_raw.get("cyclic_deps", [])) > 0
            total_loc = struct_raw.get("total_loc", 0)
            if struct_score >= 70 and not has_cyclic:
                supporting.append(f"structure: good score ({struct_score}), no cyclic deps, {total_loc} LOC")
            elif struct_score >= 50:
                supporting.append(f"structure: moderate score ({struct_score})")
            elif "poor" in finding.claim.lower() or "no" in finding.claim.lower():
                supporting.append(f"structure: low score ({struct_score}) matches claim")
            else:
                contradicting.append(f"structure: low score ({struct_score}) contradicts claim")
        else:
            supporting.append("structure analyzer ran (no data returned)")'''
        lines[start:end] = [new_method]
        v = '\n'.join(lines)

    with open(path, "w") as f:
        f.write(v)
    print(f"verification.py patched ({len(v)} chars)")


if __name__ == "__main__":
    print("Applying v2 patches...")
    patch_orchestrator()
    patch_specialists()
    patch_verification()
    print("\nAll v2 patches applied!")
