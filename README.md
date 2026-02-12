# Grainger Shipping Cost API

A FastAPI-based REST API for calculating shipping costs for Grainger orders.

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the API

Start the server:
```bash
python api.py
```

Or using uvicorn directly:
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- Interactive API docs (Swagger UI): `http://localhost:8000/docs`
- Alternative API docs (ReDoc): `http://localhost:8000/redoc`

## Endpoints

### 1. Health Check
```
GET /health
```

Response:
```json
{
  "status": "healthy"
}
```

### 2. Calculate Shipping Costs
```
POST /calculate-shipping
```

Request Body:
```json
{
  "street_address": "838 Broadway",
  "city": "New York",
  "state": "NY",
  "zipcode": "10001",
  "items": [
    {
      "sku": "52VR41",
      "quantity": 1
    },
    {
      "sku": "4YCR4",
      "quantity": 5
    },
    {
      "sku": "31CA27",
      "quantity": 100
    }
  ]
}
```

Response:
```json
{
  "success": true,
  "shipping_options": [
    {
      "shipping_method": "Ground",
      "cost": 25.50,
      "tax": 2.30,
      "estimated_delivery": "Feb 15, 2026"
    },
    {
      "shipping_method": "Expedited",
      "cost": 45.00,
      "tax": 4.05,
      "estimated_delivery": "Feb 13, 2026"
    },
    {
      "shipping_method": "Rush",
      "cost": 75.00,
      "tax": 6.75,
      "estimated_delivery": "Feb 12, 2026"
    }
  ],
  "message": "Shipping costs calculated successfully"
}
```

## Example Usage

### Using cURL:
```bash
curl -X POST "http://localhost:8000/calculate-shipping" \
  -H "Content-Type: application/json" \
  -d '{
    "street_address": "838 Broadway",
    "city": "New York",
    "state": "NY",
    "zipcode": "10001",
    "items": [
      {"sku": "52VR41", "quantity": 1},
      {"sku": "4YCR4", "quantity": 5}
    ]
  }'
```

### Using Python requests:
```python
import requests

url = "http://localhost:8000/calculate-shipping"
payload = {
    "street_address": "838 Broadway",
    "city": "New York",
    "state": "NY",
    "zipcode": "10001",
    "items": [
        {"sku": "52VR41", "quantity": 1},
        {"sku": "4YCR4", "quantity": 5},
        {"sku": "31CA27", "quantity": 100}
    ]
}

response = requests.post(url, json=payload)
print(response.json())
```

### Using JavaScript (fetch):
```javascript
const response = await fetch('http://localhost:8000/calculate-shipping', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    street_address: '838 Broadway',
    city: 'New York',
    state: 'NY',
    zipcode: '10001',
    items: [
      { sku: '52VR41', quantity: 1 },
      { sku: '4YCR4', quantity: 5 },
      { sku: '31CA27', quantity: 100 }
    ]
  })
});

const data = await response.json();
console.log(data);
```

## Request Validation

The API validates:
- **state**: Must be exactly 2 characters (automatically converted to uppercase)
- **items**: At least 1 item required
- **quantity**: Must be greater than 0

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `422`: Validation error (invalid input)
- `500`: Server error (failed to calculate shipping costs)

Error Response Example:
```json
{
  "detail": "Error calculating shipping costs: Connection timeout"
}
```

## Features

- ✅ RESTful API design
- ✅ Automatic request validation with Pydantic
- ✅ CORS enabled for cross-origin requests
- ✅ Automatic retry logic (up to 5 attempts)
- ✅ Comprehensive logging
- ✅ Interactive API documentation
- ✅ Type hints and response models

## Notes

- The API uses headless browser automation via Camoufox to obtain necessary cookies
- Requests may take 10-30 seconds due to the multi-step process
- The API implements retry logic for reliability
- All shipping methods (Ground, Expedited, Rush) are calculated in a single request
