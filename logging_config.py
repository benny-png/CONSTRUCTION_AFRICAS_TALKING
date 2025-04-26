import logging
import sys
from pprint import pformat

# Configure logging
def setup_logging():
    # Create logger
    logger = logging.getLogger("construction_api")
    logger.setLevel(logging.DEBUG)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger

# Get the logger
logger = setup_logging()

def log_request_info(request, message="Request received"):
    """Log detailed request information"""
    logger.info(f"{message}: {request.method} {request.url}")
    logger.debug(f"Request headers: {pformat(dict(request.headers))}")
    if request.method in ['POST', 'PUT', 'PATCH']:
        try:
            logger.debug(f"Request body: {pformat(request.json())}")
        except:
            logger.debug("Could not parse request body as JSON")

def log_response_info(response, message="Response sent"):
    """Log detailed response information"""
    logger.info(f"{message}: Status {response.status_code}")
    logger.debug(f"Response headers: {pformat(dict(response.headers))}")
    try:
        logger.debug(f"Response body: {pformat(response.body.decode())}")
    except:
        logger.debug("Could not decode response body") 