"""
Test script for REST API
Tests all endpoints using Python's httpx library
"""

import httpx
import sys

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_root():
    """Test root endpoint"""
    print_section("Testing Root Endpoint")
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
        print(f"✓ Root endpoint works: {data['message']}")
    return True

def test_health():
    """Test health check endpoint"""
    print_section("Testing Health Check Endpoint")
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        print(f"✓ Health check works: {data['status']}")
    return True

def test_list_items():
    """Test listing all items"""
    print_section("Testing List Items Endpoint")
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/api/items")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "items" in data
        assert "count" in data
        print(f"✓ List items works: Found {data['count']} items")
    return True

def test_create_item():
    """Test creating a new item"""
    print_section("Testing Create Item Endpoint")
    
    with httpx.Client() as client:
        # Test without JSON
        response = client.post(f"{BASE_URL}/api/items", data="test")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"✓ Correctly rejects non-JSON requests")
        
        # Test without name
        response = client.post(f"{BASE_URL}/api/items", json={"price": 10.0})
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"✓ Correctly rejects missing name")
        
        # Test with negative price
        response = client.post(f"{BASE_URL}/api/items", json={"name": "Test", "price": -5})
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"✓ Correctly rejects negative price")
        
        # Test successful creation
        response = client.post(f"{BASE_URL}/api/items",
                              json={"name": "Test Product", "price": 29.99, "description": "A test product"})
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Product"
        assert data["price"] == 29.99
        print(f"✓ Item created successfully: ID={data['id']}, Name={data['name']}")
    return data["id"]

def test_get_item(item_id):
    """Test getting a single item"""
    print_section("Testing Get Item Endpoint")
    
    with httpx.Client() as client:
        # Test existing item
        response = client.get(f"{BASE_URL}/api/items/{item_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["id"] == item_id
        print(f"✓ Get existing item works: ID={item_id}")
        
        # Test non-existing item
        response = client.get(f"{BASE_URL}/api/items/99999")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Correctly returns 404 for non-existing item")
    return True

def test_update_item(item_id):
    """Test updating an item"""
    print_section("Testing Update Item Endpoint")
    
    with httpx.Client() as client:
        # Test updating existing item
        response = client.put(f"{BASE_URL}/api/items/{item_id}",
                             json={"name": "Updated Product", "price": 39.99})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["name"] == "Updated Product"
        assert data["price"] == 39.99
        print(f"✓ Update existing item works: Name={data['name']}")
        
        # Test updating non-existing item
        response = client.put(f"{BASE_URL}/api/items/99999",
                             json={"name": "Test"})
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Correctly returns 404 for non-existing item")
        
        # Test update without name
        response = client.put(f"{BASE_URL}/api/items/{item_id}",
                             json={"price": 49.99})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Update without name works (keeps existing name)")
    return True

def test_delete_item(item_id):
    """Test deleting an item"""
    print_section("Testing Delete Item Endpoint")
    
    with httpx.Client() as client:
        # Test deleting existing item
        response = client.delete(f"{BASE_URL}/api/items/{item_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "deleted" in data["message"].lower()
        print(f"✓ Delete existing item works")
        
        # Test deleting non-existing item
        response = client.delete(f"{BASE_URL}/api/items/99999")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Correctly returns 404 for non-existing item")
    return True

def test_list_after_operations():
    """Test listing items after create/delete operations"""
    print_section("Testing List Items After Operations")
    
    with httpx.Client() as client:
        # Create a new item
        response = client.post(f"{BASE_URL}/api/items",
                              json={"name": "Final Test", "price": 15.00})
        assert response.status_code == 201
        print(f"✓ Created new item for final test")
        
        # List all items
        response = client.get(f"{BASE_URL}/api/items")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ List items shows {data['count']} items after operations")
        
        # Delete the item
        response = client.delete(f"{BASE_URL}/api/items/{data['items'][0]['id']}")
        assert response.status_code == 200
        print(f"✓ Deleted item successfully")
        
        # List again
        response = client.get(f"{BASE_URL}/api/items")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ List items shows {data['count']} items after deletion")
    return True

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  REST API TEST SUITE")
    print("="*60)
    
    tests = [
        test_root,
        test_health,
        test_list_items,
        test_create_item,
        test_get_item,
        test_update_item,
        test_delete_item,
        test_list_after_operations
    ]
    
    passed = 0
    failed = 0
    item_id = None
    
    for test in tests:
        try:
            if item_id is not None:
                item_id = test()
            else:
                test()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
    
    print_section("TEST SUMMARY")
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    print("="*60)
    
    if failed == 0:
        print("✓ ALL TESTS PASSED!")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
