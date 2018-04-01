# app.py
import asyncio
import random

from sanic import Sanic
from sanic import response
import prometheus_client as prometheus


app = Sanic()

# Initialize the metrics
counter = prometheus.Counter("sanic_requests_total",
                             "Track the total number of requests",
                             ["method", "endpoint"])


# Track the total number of requests
@app.middleware('request')
async def track_requests(request):
    # Increase the value for each requests
    # pylint: disable=E1101
    counter.labels(method=request.method,
                   endpoint=request.path).inc()


# Expose the metrics for prometheus
@app.get("/metrics")
async def metrics(request):
    output = prometheus.exposition.generate_latest().decode("utf-8")
    content_type = prometheus.exposition.CONTENT_TYPE_LATEST
    return response.text(body=output,
                         content_type=content_type)


@app.get("/")
async def index(request):
    # Simulate latency: 0ms to 1s
    latency = random.random()  # in seconds
    await asyncio.sleep(latency)
    return response.json({"message": "Hello there!"})


@app.get("/products")
async def products(request):
    products = [
        {"title": "product_a", "price": 10.0},
        {"title": "product_b", "price": 5.0},
    ]
    # Simulate latency: 0ms to 1s
    latency = random.random()  # in seconds
    await asyncio.sleep(latency)
    return response.json(products)


@app.post("/order")
async def order(request):
    # Simulate latency: 0ms to 1s
    latency = (1 - random.random())  # in seconds
    await asyncio.sleep(latency)
    return response.json({"message": "OK"})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
