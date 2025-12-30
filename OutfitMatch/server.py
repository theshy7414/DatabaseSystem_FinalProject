from flask import Flask, request, jsonify
from flask_cors import CORS
from query.query_neo4j import user_query, close_neo4j
import traceback
import logging
import sys
import datetime
import socket
from config.settings import SERVER_PORT

# Force immediate output flush
sys.stdout.reconfigure(line_buffering=True)

print("Starting server script...")

def check_port_available(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True
    except:
        return False

# Try different ports if configured port is not available
PORT = SERVER_PORT
while not check_port_available(PORT) and PORT < SERVER_PORT + 10:
    print(f"Port {PORT} is in use, trying next port...")
    PORT += 1

if PORT >= SERVER_PORT + 10:
    print("Could not find an available port!")
    sys.exit(1)

print(f"Found available port: {PORT}")

# Configure logging to output immediately
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

print("Logger configured...")

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Log all requests, before any processing
@app.before_request
def log_request_info():
    print("-------------------")
    print("New request received")
    print(f"Path: {request.path}")
    print(f"Method: {request.method}")
    print(f"Headers: {dict(request.headers)}")
    print("-------------------")

# Increase maximum content length to 16MB
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

print("Flask app configured...")

@app.route('/api/search', methods=['POST'])
def search():
    logger.debug("Received request to /api/search")
    logger.debug(f"Request headers: {dict(request.headers)}")
    logger.debug(f"Request method: {request.method}")
    
    try:
        # Log raw request data
        logger.debug(f"Request content type: {request.content_type}")
        logger.debug(f"Request content length: {request.content_length}")
        
        data = request.json
        logger.debug("Successfully parsed JSON data")
        
        if not data:
            logger.error("No JSON data received")
            return jsonify({
                'error': 'No JSON data received'
            }), 400
            
        logger.debug(f"Received data keys: {data.keys()}")
        
        if 'query_text' not in data:
            logger.error("Missing query_text field")
            return jsonify({
                'error': 'Missing required field: query_text'
            }), 400
            
        if 'image_base64' not in data:
            logger.error("Missing image_base64 field")
            return jsonify({
                'error': 'Missing required field: image_base64'
            }), 400

        query_text = data['query_text']
        image_base64 = data['image_base64']
        
        logger.debug(f"Query text: {query_text}")
        if image_base64:
            logger.debug(f"Image base64 starts with: {image_base64[:100]}...")
            logger.debug(f"Image base64 length: {len(image_base64)}")
        
        if not query_text.strip():
            logger.error("Empty query_text")
            return jsonify({
                'error': 'query_text cannot be empty'
            }), 400

        # Call the query function
        logger.debug("Calling user_query function")
        result = user_query(query_text, image_base64)
        logger.debug("user_query function returned successfully")

        # Convert products to list of dicts for JSON serialization
        if result.get('products'):
            products_list = []
            for product in result['products']:
                products_list.append({
                    'id': product[0],
                    'name': product[1],
                    'description': product[2],
                    'category': product[3],
                    'brand': product[4],
                    'price': str(product[5]) if product[5] is not None else "N/A",
                    'predicted_style': product[6] if len(product) > 6 else [],
                    'imageUrl': product[7] if len(product) > 7 and product[7] else None,
                    'shop': product[4],
                    'link': None
                })
            result['products'] = products_list
            logger.debug(f"Processed {len(products_list)} products")

        logger.debug("Sending response back to client")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500
    finally:
        logger.debug("Request completed")
        # Note: Don't close Neo4j connection here - using connection pool

@app.route('/api/test', methods=['POST'])
def test():
    print("Test endpoint called")
    try:
        data = request.json
        print(f"Received data: {data}")
        return jsonify({
            'status': 'ok',
            'received': data
        })
    except Exception as e:
        print(f"Error in test endpoint: {e}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    print("Health check endpoint called")
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("=== Starting Flask development server ===")
    print(f"Debug mode: ON")
    print(f"Host: 0.0.0.0")
    print(f"Port: {PORT}")
    print(f"Test the server with: curl http://localhost:{PORT}/api/health")
    print("=====================================")
    
    # Enable debug mode for better error messages
    app.debug = True
    try:
        app.run(host='0.0.0.0', port=PORT, threaded=True)
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1) 