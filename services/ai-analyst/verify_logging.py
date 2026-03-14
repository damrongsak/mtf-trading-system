import logging
import json
import io
import contextvars
from app.utils.middleware import setup_tracing_logging
from app.utils.tracing import request_id_ctx

def test_json_logging():
    # Setup
    log_output = io.StringIO()
    handler = logging.StreamHandler(log_output)
    
    # We need to manually inject our handler to capture output for this test
    logger = setup_tracing_logging()
    # Check if setup_logging already added a handler, if so we might need to clear it for the test
    # but let's just add ours and check the last line
    logger.addHandler(handler)
    
    # Test 1: Log without request_id
    logger.info("Test message 1")
    
    # Test 2: Log with request_id in context
    token = request_id_ctx.set("test-id-123")
    try:
        logger.info("Test message 2")
    finally:
        request_id_ctx.reset(token)
        
    output = log_output.getvalue().strip().split('\n')
    
    results = []
    for line in output:
        try:
            results.append(json.loads(line))
        except:
            pass
            
    # Verification
    assert len(results) >= 2
    assert results[-2]["message"] == "Test message 1"
    assert results[-2]["request_id"] == "" or results[-2]["request_id"] is None
    
    assert results[-1]["message"] == "Test message 2"
    assert results[-1]["request_id"] == "test-id-123"
    
    print("✅ Logging verification successful!")
    for r in results:
        print(json.dumps(r, indent=2))

if __name__ == "__main__":
    test_json_logging()
