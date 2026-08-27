"""
REST API Application using Flask
Supports:
- GET /api/items - List all items
- GET /api/items/<id> - Get item by ID
- POST /api/items - Create new item
- PUT /api/items/<id> - Update item
- DELETE /api/items/<id> - Delete item
- GET /api/health - Health check endpoint
"""

from flask import Flask, request, jsonify
from datetime import datetime
import uuid

app = Flask(__name__)

# In-memory data store
items_db = {}
next_id = 1

# Error handling decorators
@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad Request", "message": str(error)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not Found", "message": "Resource not found"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method Not Allowed", "message": str(error)}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal Server Error", "message": str(error)}), 500


# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }), 200


# List all items
@app.route('/api/items', methods=['GET'])
def get_items():
    """Get all items"""
    items_list = []
    for item_id, item in items_db.items():
        items_list.append({
            "id": item_id,
            "name": item["name"],
            "description": item["description"],
            "price": item["price"],
            "created_at": item["created_at"]
        })
    return jsonify({"items": items_list, "count": len(items_list)}), 200


# Get single item by ID
@app.route('/api/items/<item_id>', methods=['GET'])
def get_item(item_id):
    """Get item by ID"""
    if item_id not in items_db:
        return jsonify({"error": "Not Found", "message": f"Item with ID {item_id} not found"}), 404
    
    item = items_db[item_id]
    return jsonify({
        "id": item_id,
        "name": item["name"],
        "description": item["description"],
        "price": item["price"],
        "created_at": item["created_at"]
    }), 200


# Create new item
@app.route('/api/items', methods=['POST'])
def create_item():
    """Create a new item"""
    global next_id
    
    # Validate request data
    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    # Check required fields
    if "name" not in data or not data["name"]:
        return jsonify({"error": "Bad Request", "message": "Name is required"}), 400
    
    if "price" not in data or data["price"] is None:
        return jsonify({"error": "Bad Request", "message": "Price is required"}), 400
    
    if data["price"] < 0:
        return jsonify({"error": "Bad Request", "message": "Price cannot be negative"}), 400
    
    # Generate new ID
    new_id = str(next_id)
    next_id += 1
    
    # Create item
    new_item = {
        "id": new_id,
        "name": data["name"],
        "description": data.get("description", ""),
        "price": data["price"],
        "created_at": datetime.utcnow().isoformat()
    }
    
    items_db[new_id] = new_item
    
    return jsonify(new_item), 201


# Update item
@app.route('/api/items/<item_id>', methods=['PUT'])
def update_item(item_id):
    """Update an existing item"""
    # Check if item exists
    if item_id not in items_db:
        return jsonify({"error": "Not Found", "message": f"Item with ID {item_id} not found"}), 404
    
    # Validate request data
    if not request.is_json:
        return jsonify({"error": "Bad Request", "message": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    # Check if name is provided (required field)
    if "name" not in data or not data["name"]:
        return jsonify({"error": "Bad Request", "message": "Name is required"}), 400
    
    # Validate price if provided
    if "price" in data:
        if data["price"] is None:
            return jsonify({"error": "Bad Request", "message": "Price is required"}), 400
        if data["price"] < 0:
            return jsonify({"error": "Bad Request", "message": "Price cannot be negative"}), 400
    
    # Update item
    items_db[item_id]["name"] = data["name"]
    if "description" in data:
        items_db[item_id]["description"] = data["description"]
    if "price" in data:
        items_db[item_id]["price"] = data["price"]
    
    return jsonify(items_db[item_id]), 200


# Delete item
@app.route('/api/items/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    """Delete an item"""
    # Check if item exists
    if item_id not in items_db:
        return jsonify({"error": "Not Found", "message": f"Item with ID {item_id} not found"}), 404
    
    # Delete item
    del items_db[item_id]
    
    return jsonify({"message": f"Item {item_id} deleted successfully"}), 200


# Root endpoint
@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information"""
    return jsonify({
        "message": "Welcome to the REST API",
        "version": "1.0.0",
        "endpoints": {
            "GET /api/health": "Health check",
            "GET /api/items": "List all items",
            "GET /api/items/<id>": "Get item by ID",
            "POST /api/items": "Create new item",
            "PUT /api/items/<id>": "Update item",
            "DELETE /api/items/<id>": "Delete item"
        }
    }), 200


if __name__ == '__main__':
    print("=" * 60)
    print("REST API Server Starting...")
    print("=" * 60)
    print("Available endpoints:")
    print("  GET  /              - API information")
    print("  GET  /api/health    - Health check")
    print("  GET  /api/items     - List all items")
    print("  GET  /api/items/<id> - Get item by ID")
    print("  POST /api/items     - Create new item")
    print("  PUT  /api/items/<id> - Update item")
    print("  DELETE /api/items/<id> - Delete item")
    print("=" * 60)
    print("Starting server on http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
