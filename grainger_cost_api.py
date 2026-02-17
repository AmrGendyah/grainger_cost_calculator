from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
import asyncio
import logging
from camoufox.async_api import AsyncCamoufox
from curl_cffi import requests
import re


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize FastAPI app
app = FastAPI(
    title="Grainger Shipping Cost API",
    description="API to calculate shipping costs for Grainger orders",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class ItemInput(BaseModel):
    sku: str = Field(..., description="Product SKU code")
    quantity: int = Field(..., gt=0, description="Quantity of the item")

class ShippingRequest(BaseModel):
    street_address: str = Field(..., description="Street address for delivery")
    city: str = Field(..., description="City for delivery")
    state: str = Field(..., min_length=2, max_length=2, description="Two-letter state code")
    zipcode: str = Field(..., description="ZIP code for delivery")
    items: List[ItemInput] = Field(..., min_items=1, description="List of items to order")
    
    @validator('state')
    def state_must_be_uppercase(cls, v):
        return v.upper()

class ShippingCostResponse(BaseModel):
    shipping_method: str
    cost: Optional[float]
    tax: Optional[float]
    estimated_delivery: Optional[str]

class ShippingResponse(BaseModel):
    success: bool
    shipping_options: List[ShippingCostResponse]
    message: Optional[str] = None

# Helper functions from original script
def extract_strong_text(html):
    match = re.search(r"<strong>(.*?)</strong>", html, re.IGNORECASE)
    return match.group(1).strip() if match else None

def add_items_data(prd_items):
    data_dict = {}
    for i, prd in enumerate(prd_items):
        data_dict[f'cartEntries[{i}].sku'] = prd['sku']
        data_dict[f'cartEntries[{i}].quantity'] = prd['quantity']
    return data_dict

async def req_sessions():
    session = requests.AsyncSession(impersonate='chrome')
    return session

async def get_main_cookies():
    async with AsyncCamoufox(humanize=True, headless=True, locale="en-US") as browser:
        page = await browser.new_page()
        await page.goto('https://www.grainger.com/content/bulk-order-pad')
        response_cookies = await page.context.cookies()
        await page.close()
        res_cookies = {cookie['name']: cookie['value'] for cookie in response_cookies}
        logging.info("✅ New Cookies Created with AsyncCamoufox")
    return res_cookies


async def start_connection(session, cookies):
    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'en-US,en;q=0.9,ar;q=0.8',
        'dnt': '1',
        'priority': 'u=1, i',
        'referer': 'https://www.grainger.com/guestcheckout/shipping',
        'sec-ch-device-memory': '8',
        'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-full-version-list': '"Google Chrome";v="135.0.7049.85", "Not-A.Brand";v="8.0.0.0", "Chromium";v="135.0.7049.85"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }

    params = {
        'domain': 'www.grainger.com',
    }

    response = await session.get('https://www.grainger.com/GenericController', cookies=cookies, params=params, headers=headers)
    logging.info(f"✅ Start_connection Status => {response.status_code}")
    jsbd = response.json()
    tokenKey = jsbd.get('tokenKey')
    tokenValue = jsbd.get('tokenValue')
    return response, tokenKey, tokenValue

async def signin(session):
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9,ar;q=0.8',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'dnt': '1',
        'origin': 'https://www.grainger.com',
        'priority': 'u=0, i',
        'referer': 'https://www.grainger.com/myaccount/checkoutsignin',
        'sec-ch-device-memory': '8',
        'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-full-version-list': '"Google Chrome";v="135.0.7049.85", "Not-A.Brand";v="8.0.0.0", "Chromium";v="135.0.7049.85"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    }

    data = {
        'countryCode': 'US',
        'guestcheckout': 'true',
    }

    response = await session.post('https://www.grainger.com/checkout/guest', headers=headers, data=data)
    logging.info(f"✅ Sign in Status => {response.status_code}")
    resp_cookies = response.cookies.get_dict()
    return resp_cookies

async def add_items(session, tokenKey, tokenValue, items):
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,ar;q=0.8',
        'content-type': 'application/x-www-form-urlencoded',
        'contenttype': 'application/x-www-form-urlencoded',
        'dnt': '1',
        'origin': 'https://www.grainger.com',
        'priority': 'u=1, i',
        'referer': 'https://www.grainger.com/content/bulk-order-pad',
        'sec-ch-device-memory': '8',
        'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-full-version-list': '"Google Chrome";v="135.0.7049.85", "Not-A.Brand";v="8.0.0.0", "Chromium";v="135.0.7049.85"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }

    payload = add_items_data(items)
    payload[tokenKey] = tokenValue
    response = await session.post('https://www.grainger.com/cart/v2/addItems', headers=headers, data=payload)
    logging.info(f"✅ add_items Status => {response.status_code}")
    resp_cookies = response.cookies.get_dict()
    return resp_cookies

async def get_final_cost(session, street_address, city, state, zipcode):
    headers = {
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9,ar;q=0.8',
        'dnt': '1',
        'priority': 'u=1, i',
        'referer': 'https://www.grainger.com/guestcheckout/shipping',
        'sec-ch-device-memory': '8',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-full-version-list': '"Not(A:Brand";v="8.0.0.0", "Chromium";v="144.0.7559.133", "Google Chrome";v="144.0.7559.133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    }

    json_data = {
        'recipientFirstName': 'dummy',
        'recipientLastName': 'gust',
        'address1': street_address,
        'city': city,
        'state': state,
        'zipCode': zipcode,
        'recipientEmail': 'trdrtgst@htftgfhj.com',
        'guestOptInEmailMarketing': 'on',
        'recipientPhone': '(784)674-8784',
        'shippingMethod': 'GR'
    }

    response = await session.post('https://www.grainger.com/guestcheckout/shipping', headers=headers, json=json_data)
    logging.info(f"✅ get_final_shipping_cost Status => {response.status_code}")
    return response

async def payment_method(session):
    headers = {
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9,ar;q=0.8',
        'dnt': '1',
        'priority': 'u=1, i',
        'referer': 'https://www.grainger.com/guestcheckout/shipping',
        'sec-ch-device-memory': '8',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-full-version-list': '"Not(A:Brand";v="8.0.0.0", "Chromium";v="144.0.7559.133", "Google Chrome";v="144.0.7559.133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    }

    response = await session.get('https://www.grainger.com/guestcheckout/payment', headers=headers)
    logging.info(f"✅ payment_method Status => {response.status_code}")
    return response

async def calculate_shipping_cost(items, street_address, city, state, zipcode):
    MAX_RETRIES = 5
    retry = 1
    cost_list = []
    
    # Convert ItemInput objects to dict format
    items_dict = [{'sku': item.sku, 'quantity': item.quantity} for item in items]
    
    while retry <= MAX_RETRIES:
        try:
            session = await req_sessions()
            main_cookies = await get_main_cookies()
            response, tokenKey, tokenValue = await start_connection(session, main_cookies)
            
            if response.status_code == 200:
                await add_items(session, tokenKey, tokenValue, items_dict)
                await signin(session)
                
                shipping_cost = await get_final_cost(session, street_address=street_address,
                                                    city=city, state=state, zipcode=zipcode)
                
                cart_data = shipping_cost.json().get('cart', {})
                groundDeliveryCost = cart_data.get('groundDeliveryCost')
                groundtax = cart_data.get('groundTaxCost')
                ExpeditedCost = cart_data.get('twoDayDeliveryCost')
                Expeditedtax = cart_data.get('twoDayTaxCost')
                rushCost = cart_data.get('oneDayDeliveryCost')
                rushtax = cart_data.get('oneDayTaxCost')
                
                cost_list = [
                    {
                        'shipping_method': 'Ground',
                        'cost': groundDeliveryCost,
                        'tax': groundtax,
                        'estimated_delivery': None
                    },
                    {
                        'shipping_method': 'Expedited',
                        'cost': ExpeditedCost,
                        'tax': Expeditedtax,
                        'estimated_delivery': None
                    },
                    {
                        'shipping_method': 'Rush',
                        'cost': rushCost,
                        'tax': rushtax,
                        'estimated_delivery': None
                    }
                ]
                
                resp = await payment_method(session)
                levels = resp.json().get('view', {}).get('data', {}).get('cart', {}).get('deliveryMode', {}).get('serviceLevelOptions', {}).get('serviceLevels', [])
                
                for level in levels:
                    name = level.get('name', '').lower()
                    deliver_date = level.get('availabilityMessage', '')
                    for cost_dict in cost_list:
                        if cost_dict['shipping_method'].lower().strip() == name.lower().strip():
                            cost_dict['estimated_delivery'] = extract_strong_text(deliver_date)
                
                logging.info("✅ Successfully retrieved shipping costs.")
                await session.close()
                break
            else:
                retry += 1
                await session.close()
        except Exception as e:
            logging.error(f"❌ Error on attempt {retry}: {e}")
            retry += 1
            await session.close()
            if retry > MAX_RETRIES:
                raise

    return cost_list

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Grainger Shipping Cost API",
        "version": "1.0.0",
        "endpoints": {
            "/calculate-shipping": "POST - Calculate shipping costs",
            "/health": "GET - Health check"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/calculate_shipping", response_model=ShippingResponse)
async def calculate_shipping(request: ShippingRequest):
    """
    Calculate shipping costs for a Grainger order.
    
    - **street_address**: Street address for delivery
    - **city**: City for delivery
    - **state**: Two-letter state code (e.g., NY, CA)
    - **zipcode**: ZIP code for delivery
    - **items**: List of items with SKU and quantity
    """
    try:
        logging.info(f"Calculating shipping for {len(request.items)} items to {request.city}, {request.state}")
        
        cost_list = await calculate_shipping_cost(
            items=request.items,
            street_address=request.street_address,
            city=request.city,
            state=request.state,
            zipcode=request.zipcode
        )
        
        if not cost_list:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve shipping costs after multiple attempts"
            )
        
        shipping_options = [ShippingCostResponse(**item) for item in cost_list]
        
        return ShippingResponse(
            success=True,
            shipping_options=shipping_options,
            message="Shipping costs calculated successfully"
        )
        
    except Exception as e:
        logging.error(f"Error calculating shipping: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating shipping costs: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)




