import json
import math
from http import HTTPStatus
from typing import Any, Callable, Awaitable


async def app(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    """
    ASGI приложение для обработки HTTP запросов, включая вычисление факториала,
    последовательности Фибоначчи и среднего арифметического.

    Args:
        scope: Словарь, содержащий информацию о запросе.
        receive: Функция для получения сообщений.
        send: Функция для отправки сообщений.
    """
    if scope["type"] == "lifespan":
        while True:
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif msg["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    assert scope["type"] == "http"
    method = scope["method"]
    path = scope["path"]

    async def json_response(status: int, content: dict) -> None:
        """
        Отправляет JSON ответ.

        Args:
            status: HTTP статус ответа.
            content: Содержимое ответа в формате словаря.
        """
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {"type": "http.response.body", "body": json.dumps(content).encode("utf-8")}
        )

    if path == "/factorial" and method == "GET":
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = dict(
            param.split("=") for param in query_string.split("&") if "=" in param
        )
        n = params.get("n")

        if n is None or not n.lstrip("-").isdigit():
            await json_response(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"detail": "Parameter 'n' is required and must be a valid integer."},
            )
            return

        n = int(n)

        if n < 0:
            await json_response(
                HTTPStatus.BAD_REQUEST,
                {"detail": "Invalid value for 'n', must be non-negative."},
            )
            return

        result = math.factorial(n)
        await json_response(HTTPStatus.OK, {"result": result})

    elif path.startswith("/fibonacci/") and method == "GET":
        try:
            n = int(path.split("/")[2])
        except (IndexError, ValueError):
            await json_response(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"detail": "Path parameter 'n' must be a valid integer."},
            )
            return

        if n < 0:
            await json_response(
                HTTPStatus.BAD_REQUEST,
                {"detail": "Invalid value for 'n', must be non-negative."},
            )
            return

        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b

        await json_response(HTTPStatus.OK, {"result": b})

    elif path == "/mean" and method == "GET":
        request = await receive()
        try:
            body = json.loads(request.get("body", b"").decode("utf-8"))
            if not isinstance(body, list) or not all(
                isinstance(i, (float, int)) for i in body
            ):
                raise ValueError
        except ValueError:
            await json_response(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"detail": "Request body must be a non-empty array of floats."},
            )
            return

        if not body:
            await json_response(
                HTTPStatus.BAD_REQUEST,
                {
                    "detail": "Invalid value for body, must be a non-empty array of floats."
                },
            )
            return

        result = sum(body) / len(body)
        await json_response(HTTPStatus.OK, {"result": result})

    else:
        await send(
            {
                "type": "http.response.start",
                "status": HTTPStatus.NOT_FOUND,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"404 Not Found"})
