#!/bin/bash
# Re-verify coverage with strict timeouts to prevent hangs
export PYTHONPATH=$PYTHONPATH:.
export PYTHONUNBUFFERED=1

echo "🔍 Starting Internal Ingestor Coverage Audit..."

# We run pytest on each file individually to isolate the hang
FILES=("tests/test_boot.py" "tests/test_orchestrator_v2.py" "tests/test_ontology_v2.py" "tests/test_api_v2_e2e.py")

for f in "${FILES[@]}"; do
    echo "Testing $f..."
    timeout 60 pytest "$f" -v || echo "⚠️ $f failed or timed out"
done

echo "📊 Generating Final Coverage Report..."
pytest --cov=app --cov-report=term-missing "${FILES[@]}"
