from fastapi import FastAPI, Response, HTTPException, Query, status
from pydantic import BaseModel
from typing import List, Dict, Optional
from dataclasses import dataclass, field

app = FastAPI(title="My Shop Server")

cart_storage: Dict[int, "ShoppingCart"] = {}
item_storage: Dict[int, "Product"] = {}


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
    quantity: int = 0


@app.post("/cart", status_code=status.HTTP_201_CREATED)
def create_shopping_cart(response: Response):
    """
    Создает новую корзину и возвращает ее идентификатор.

    Parameters:
    - response: объект Response для добавления заголовков.

    Returns:
    - JSON-объект с идентификатором созданной корзины.
    """
    cart_id = len(cart_storage) + 1
    cart_storage[cart_id] = ShoppingCart(id=cart_id)
    response.headers["location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@app.get("/cart/{cart_id}")
def retrieve_cart(cart_id: int) -> ShoppingCart:
    """
    Возвращает корзину по ее идентификатору.

    Parameters:
    - cart_id: идентификатор корзины.

    Returns:
    - JSON-объект с данными корзины.

    Raises:
    - HTTPException: если корзина не найдена.
    """
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
    """
    Возвращает список корзин с возможностью фильтрации.

    Parameters:
    - offset: количество пропускаемых элементов.
    - limit: максимальное количество возвращаемых элементов.
    - min_price: минимальная цена корзины.
    - max_price: максимальная цена корзины.
    - min_quantity: минимальное количество товаров в корзине.
    - max_quantity: максимальное количество товаров в корзине.

    Returns:
    - Список корзин, соответствующих критериям фильтрации.
    """
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


@app.patch("/item/{product_id}")
def partial_update_product(product_id: int, product_data: dict):
    """
    Частично обновляет данные продукта по его идентификатору.

    Parameters:
    - product_id: идентификатор продукта.
    - product_data: словарь с обновляемыми данными.

    Returns:
    - Обновленный объект продукта.

    Raises:
    - HTTPException: если продукт не найден или поле невалидное.
    """
    if product_id not in item_storage:
        raise HTTPException(status_code=404, detail="Item not found")
    if item_storage[product_id].deleted:
        raise HTTPException(status_code=304, detail="Not modified")
    for field in product_data:
        if field not in {"name", "price"}:
            raise HTTPException(status_code=422, detail="Invalid field")
        setattr(item_storage[product_id], field, product_data[field])
    return item_storage[product_id]


@app.post("/item", status_code=status.HTTP_201_CREATED)
def create_product(product_data: dict, response: Response):
    """
    Создает новый продукт и возвращает его данные.

    Parameters:
    - product_data: словарь с данными нового продукта.
    - response: объект Response для добавления заголовков.

    Returns:
    - JSON-объект с данными созданного продукта.
    """
    product_id = len(item_storage) + 1
    item_storage[product_id] = Product(
        id=product_id, name=product_data["name"], price=product_data["price"]
    )
    response.headers["location"] = f"/item/{product_id}"
    return item_storage[product_id]


@app.get("/item/{product_id}")
def retrieve_product(product_id: int):
    """
    Возвращает продукт по его идентификатору.

    Parameters:
    - product_id: идентификатор продукта.

    Returns:
    - JSON-объект с данными продукта.

    Raises:
    - HTTPException: если продукт не найден или удален.
    """
    if product_id not in item_storage:
        raise HTTPException(status_code=404, detail="Item not found")
    if item_storage[product_id].deleted:
        raise HTTPException(status_code=404, detail="Item not found (deleted)")
    return item_storage[product_id]


@app.get("/item")
def list_products(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = Query(False),
):
    """
    Возвращает список продуктов с возможностью фильтрации.

    Parameters:
    - offset: количество пропускаемых элементов.
    - limit: максимальное количество возвращаемых элементов.
    - min_price: минимальная цена продукта.
    - max_price: максимальная цена продукта.
    - show_deleted: флаг для отображения удаленных продуктов.

    Returns:
    - Список продуктов, соответствующих критериям фильтрации.
    """
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
    """
    Помечает продукт как удаленный.

    Parameters:
    - product_id: идентификатор продукта.

    Returns:
    - Сообщение о результате операции.

    Raises:
    - HTTPException: если продукт не найден или уже удален.
    """
    if product_id not in item_storage:
        raise HTTPException(status_code=404, detail="Item not found")
    if item_storage[product_id].deleted:
        return {"message": "Item already marked as deleted"}
    item_storage[product_id].deleted = True
    return {"message": "Item marked as deleted"}


@app.post("/cart/{cart_id}/add/{item_id}")
def add_product_to_cart(cart_id: int, item_id: int):
    """
    Добавляет продукт в корзину.

    Parameters:
    - cart_id: идентификатор корзины.
    - item_id: идентификатор продукта.

    Returns:
    - Сообщение о результате операции.

    Raises:
    - HTTPException: если корзина или продукт не найдены.
    """
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


@app.put("/item/{product_id}")
def update_product(product_id: int, product_data: dict):
    """
    Обновляет данные продукта по его идентификатору.

    Parameters:
    - product_id: идентификатор продукта.
    - product_data: словарь с обновляемыми данными.

    Returns:
    - Обновленный объект продукта.

    Raises:
    - HTTPException: если продукт не найден, удален или переданы некорректные поля.
    """
    if product_id not in item_storage:
        raise HTTPException(status_code=404, detail="Item not found")
    if item_storage[product_id].deleted:
        raise HTTPException(status_code=304, detail="Not modified")
    if "name" in product_data and "price" in product_data:
        item_storage[product_id].name = product_data["name"]
        item_storage[product_id].price = product_data["price"]
        return item_storage[product_id]
    else:
        raise HTTPException(status_code=422, detail="Invalid field")
