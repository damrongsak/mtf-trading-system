import logging
import json
import io
from app.logging_config import setup_logging
from app.utils.tracing import request_id_ctx

def test_json_logging():
    log_output = io.StringIO()
    handler = logging.StreamHandler(log_output)
    
    # Setup standard logger
    setup_logging()
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    
    # Test 1: No request_id
    root_logger.info("Data pipeline test 1")
    
    # Test 2: With request_id
    token = request_id_ctx.set("data-pipeline-id-999")
    try:
        root_logger.info("Data pipeline test 2")
    finally:
        request_id_ctx.reset(token)
        
    output = log_output.getvalue().strip().split('\n')
    results = [json.loads(line) for line in output if line.startswith('{')]
    
    assert any(r["message"] == "Data pipeline test 2" and r["request_id"] == "data-pipeline-id-999" for r in results)
    print("✅ Data Pipeline Logging Verified!")
    for r in results:
        print(json.dumps(r))

if __name__ == "__main__":
    test_json_logging()
