from fastapi import (
    FastAPI,
    HTTPException,
    status,
    Query,
    Body,
    Response,
    WebSocket,
    WebSocketDisconnect,
    Request,
)
from pydantic import BaseModel
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from prometheus_client import Counter, Histogram, start_http_server, generate_latest
from contextlib import asynccontextmanager

app = FastAPI(title="My Shop Server")

# Хранение данных
cart_storage: Dict[int, "ShoppingCart"] = {}
item_storage: Dict[int, "Product"] = {}


# Модели данных
@dataclass
class Product:
    id: int
    name: str
    price: float
    deleted: bool = False


@dataclass
class CartProduct:
    id: int
    name: str
    quantity: int
    available: bool


@dataclass
class ShoppingCart:
    id: int
    items: List[CartProduct] = field(default_factory=list)
    price: float = 0.0
    quantity: int = 0.0


# Статистика Prometheus
REQUEST_COUNT = Counter("request_count", "Количество запросов")
REQUEST_LATENCY = Histogram("request_latency_seconds", "Время обработки запросов")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_http_server(8001)  # Запуск Prometheus-сервера для метрик
    yield


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/metrics")
async def get_metrics():

    return Response(generate_latest(), media_type="text/plain")


@app.middleware("http")
async def add_prometheus_metrics(request: Request, call_next):

    REQUEST_COUNT.inc()

    with REQUEST_LATENCY.time():

        response = await call_next(request)

    return response


@app.get("/")
def read_root():
    return {"message": "API is running"}


@app.post("/cart", status_code=status.HTTP_201_CREATED)
def create_cart(response: Response):
    cart_id = len(cart_storage) + 1
    cart_storage[cart_id] = ShoppingCart(id=cart_id)
    response.headers["location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@app.get("/cart/{cart_id}")
def retrieve_cart(cart_id: int) -> ShoppingCart:
    if cart_id not in cart_storage:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart_storage[cart_id]


@app.get("/cart")
def list_shopping_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    filtered_carts = [
        cart
        for cart in cart_storage.values()
        if (
            (min_price is None or cart.price >= min_price)
            and (max_price is None or cart.price <= max_price)
            and (
                min_quantity is None
                or sum(item.quantity for item in cart.items) >= min_quantity
            )
            and (
                max_quantity is None
                or sum(item.quantity for item in cart.items) <= max_quantity
            )
        )
    ]
    return filtered_carts[offset : offset + limit]


@app.post("/item", status_code=status.HTTP_201_CREATED)
def create_product(product_data: dict, response: Response):
    product_id = len(item_storage) + 1
    item_storage[product_id] = Product(
        id=product_id, name=product_data["name"], price=product_data["price"]
    )
    response.headers["location"] = f"/item/{product_id}"
    return item_storage[product_id]


@app.get("/item/{product_id}")
def retrieve_product(product_id: int):
    if product_id not in item_storage or item_storage[product_id].deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return item_storage[product_id]


@app.get("/item")
def list_products(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = Query(False),
):
    filtered_items = [
        item
        for item in item_storage.values()
        if (
            (show_deleted or not item.deleted)
            and (min_price is None or item.price >= min_price)
            and (max_price is None or item.price <= max_price)
        )
    ]
    return filtered_items[offset : offset + limit]


@app.delete("/item/{product_id}")
def delete_product(product_id: int):
    if product_id not in item_storage:
        raise HTTPException(status_code=404, detail="Item not found")
    if item_storage[product_id].deleted:
        return {"message": "Item already marked as deleted"}
    item_storage[product_id].deleted = True
    return {"message": "Item marked as deleted"}


@app.post("/cart/{cart_id}/add/{item_id}")
def add_product_to_cart(cart_id: int, item_id: int):
    if cart_id not in cart_storage:
        raise HTTPException(status_code=404, detail="Cart not found")
    if item_id not in item_storage:
        raise HTTPException(status_code=404, detail="Item not found")

    cart = cart_storage[cart_id]
    item = item_storage[item_id]

    for cart_product in cart.items:
        if cart_product.id == item_id:
            cart_product.quantity += 1
            break
    else:
        cart.items.append(
            CartProduct(
                id=item.id, name=item.name, quantity=1, available=not item.deleted
            )
        )

    cart.price += item.price
    cart.quantity += 1
    return {"message": "Item added to cart"}


@app.patch("/item/{product_id}")
def partial_update_product(product_id: int, product_data: dict):
    if product_id not in item_storage or item_storage[product_id].deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    for field in product_data:
        if field not in {"name", "price"}:
            raise HTTPException(status_code=422, detail="Invalid field")
        setattr(item_storage[product_id], field, product_data[field])
    return item_storage[product_id]


@app.put("/item/{product_id}")
def update_product(product_id: int, product_data: dict):
    if product_id not in item_storage or item_storage[product_id].deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    if "name" in product_data and "price" in product_data:
        item_storage[product_id].name = product_data["name"]
        item_storage[product_id].price = product_data["price"]
        return item_storage[product_id]
    else:
        raise HTTPException(status_code=422, detail="Invalid field")
