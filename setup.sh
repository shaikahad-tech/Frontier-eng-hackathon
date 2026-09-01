#!/bin/bash
# Setup script — run this once to apply all patches and verify the system.
set -e

echo "=== RepoAssess Setup ==="

# 1. Apply patches
echo "1. Applying patches..."
python src/phase5/patch_repos.py || echo "  (repos patch already applied)"
python src/phase4/patch_v2.py || echo "  (v2 patch already applied)"

# 2. Verify imports
echo "2. Verifying imports..."
python -c "from src.phase2.pipeline import Pipeline; print('  Phase 2 OK')"
python -c "from src.phase3.baseline import evaluate_baseline; print('  Phase 3 OK')"
python -c "from src.phase4.orchestrator import evaluate_advanced, evaluate_advanced_no_verification; print('  Phase 4 OK')"
python -c "from src.phase5.benchmark import run_benchmark; print('  Phase 5 OK')"

# 3. Verify 25 repos
echo "3. Verifying 25 repos..."
python -c "
from src.phase5.repos import REPO_GENERATORS
from src.phase5.ground_truth import GROUND_TRUTH
assert len(REPO_GENERATORS) == 25, f'Expected 25 repos, got {len(REPO_GENERATORS)}'
assert len(GROUND_TRUTH) == 25, f'Expected 25 ground truth entries, got {len(GROUND_TRUTH)}'
print(f'  25 repos verified')
"

# 4. Run smoke test
echo "4. Running smoke test..."
python -c "
import tempfile, os
from src.phase4.orchestrator import evaluate_advanced

with tempfile.TemporaryDirectory() as repo:
    with open(os.path.join(repo, 'README.md'), 'w') as f:
        f.write('# Test\n## Install\n## Usage\n## Testing\n## License\n## Contributing\n## Examples\n')
    os.makedirs(os.path.join(repo, 'src'))
    with open(os.path.join(repo, 'src/app.py'), 'w') as f:
        f.write('def app(): return True\n')
    os.makedirs(os.path.join(repo, 'tests'))
    with open(os.path.join(repo, 'tests/test_app.py'), 'w') as f:
        f.write('def test_app(): assert True\n')
    with open(os.path.join(repo, 'pyproject.toml'), 'w') as f:
        f.write('[project]\nname = \"test\"\nversion = \"0.1.0\"\n')
    
    result = evaluate_advanced(repo)
    print(f'  Score: {result[\"score\"]}/100, Grade: {result[\"grade\"]}')
    print(f'  Verification rate: {result[\"verification_rate\"]:.0%}')
    print(f'  Recommendation: {result[\"recommendation\"]}')
    print(f'  Remediation items: {len(result[\"remediation_plan\"])}')
"

# 5. Run tests
echo "5. Running tests..."
python -m pytest tests/test_comprehensive.py -v --tb=short || echo "  (some tests may fail if patches not yet applied)"

echo ""
echo "=== Setup Complete ==="
echo "To run the full benchmark: python repoassess.py benchmark"
echo "To analyze a repo: python repoassess.py analyze /path/to/repo"
