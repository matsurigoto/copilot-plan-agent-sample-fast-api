import random
import threading
from decimal import Decimal
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Item Management API", description="API for managing items with random fruit names")

# Random fruit names for items
FRUIT_NAMES = [
    "Apple", "Banana", "Cherry", "Durian", "Elderberry",
    "Fig", "Grape", "Honeydew", "Jackfruit", "Kiwi",
    "Lemon", "Mango", "Nectarine", "Orange", "Papaya",
    "Quince", "Raspberry", "Strawberry", "Tangerine", "Watermelon"
]

# Thread-safe in-memory storage for items
items_db: dict[int, dict] = {}
items_lock = threading.Lock()
item_id_counter = 0
counter_lock = threading.Lock()


class ItemCreate(BaseModel):
    name: Optional[str] = None  # If not provided, will use random fruit name
    price: Decimal = Field(..., gt=0, description="Price must be a positive number")
    description: str = Field(..., min_length=1, description="Description cannot be empty")

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Description cannot be empty or whitespace only")
        return v


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0, description="Price must be a positive number")
    description: Optional[str] = Field(None, min_length=1, description="Description cannot be empty")

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Description cannot be empty or whitespace only")
        return v


class Item(BaseModel):
    id: int
    name: str
    price: Decimal
    description: str


class ItemPrice(BaseModel):
    id: int
    name: str
    price: Decimal


class StatusResponse(BaseModel):
    status: str
    message: str


@app.get("/status", response_model=StatusResponse)
def get_status():
    """Get the status of the API."""
    return StatusResponse(status="ok", message="API is running")


@app.post("/items", response_model=Item)
def create_item(item: ItemCreate):
    """Create a new item. If name is not provided, a random fruit name will be used."""
    global item_id_counter
    
    with counter_lock:
        item_id_counter += 1
        new_id = item_id_counter
    
    name = item.name if item.name else random.choice(FRUIT_NAMES)
    
    new_item = {
        "id": new_id,
        "name": name,
        "price": item.price,
        "description": item.description
    }
    
    with items_lock:
        items_db[new_id] = new_item
    
    return Item(**new_item)


@app.get("/items", response_model=list[Item])
def get_items():
    """Get all items."""
    with items_lock:
        return [Item(**item) for item in items_db.values()]


@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    """Get a specific item by ID."""
    with items_lock:
        if item_id not in items_db:
            raise HTTPException(status_code=404, detail="Item not found")
        return Item(**items_db[item_id])


@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, item: ItemUpdate):
    """Update an existing item."""
    with items_lock:
        if item_id not in items_db:
            raise HTTPException(status_code=404, detail="Item not found")
        
        existing_item = items_db[item_id]
        
        if item.name is not None:
            existing_item["name"] = item.name
        if item.price is not None:
            existing_item["price"] = item.price
        if item.description is not None:
            existing_item["description"] = item.description
        
        items_db[item_id] = existing_item
        return Item(**existing_item)


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    """Delete an item."""
    with items_lock:
        if item_id not in items_db:
            raise HTTPException(status_code=404, detail="Item not found")
        
        del items_db[item_id]
    return {"message": "Item deleted successfully"}


@app.get("/items/{item_id}/price", response_model=ItemPrice)
def get_item_price(item_id: int):
    """Get the price of a specific item."""
    with items_lock:
        if item_id not in items_db:
            raise HTTPException(status_code=404, detail="Item not found")
        
        item = items_db[item_id]
        return ItemPrice(id=item["id"], name=item["name"], price=item["price"])
