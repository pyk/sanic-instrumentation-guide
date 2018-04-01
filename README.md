# A Guide to Instrument Sanic Application

**NOTE: This guide is in progress**

In this repository contains a guide on how to collect metrics from
your Sanic Application.

TODO: add example dashboard here

These are metrics that we will collect from our Sanic application:

* Request rate (per second)
* Request duration (in millisecond)
* Error rate (4xx or 5xx responses)


## Instrumentation Stack
We will use these tools:

* [Prometheus](https://prometheus.io): For storing the metrics data
* [Grafana](https://grafana.com/): For exploring the metrics data

### Prometheus
Prometheus is an open-source systems monitoring and alerting toolkit originally
built at SoundCloud. You can install and run the prometheus by following this
[guide](https://prometheus.io/docs/introduction/first_steps/).

For this guide, I use a docker container to run the prometheus instance:

```bash
docker run --rm -p 9090:9090 \
    -v $PWD/prometheus/:/etc/prometheus/ \
    prom/prometheus:v2.1.0 \
    --config.file=/etc/prometheus/config.yaml \
    --storage.tsdb.path=/etc/prometheus/data
```

The prometheus instance is accessible at [http://localhost:9090](http://localhost:9090).

### Grafana
Grafana is the open platform for beautiful analytics and monitoring. You can install
and run the Grafana by following this [guide](https://grafana.com/get).

For this guide, I use a docker container to run the grafana instance:

```bash
docker run --rm -p 3000:3000 \
      -v $PWD/grafana:/var/lib/grafana \
      grafana/grafana:5.0.4
```

The grafana instance is accessible at [http://localhost:3000](http://localhost:3000).


## Tutorial
Suppose that we have the following Sanic app that we want to monitor:

```python
# app.py
import asyncio
import random

from sanic import Sanic
from sanic import response

app = Sanic()


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

There are 3 dummy endpoints:

1. `GET /`. It returns a simple JSON that says hello.
2. `GET /prodcuts`. It returns a list of dummy products.
3. `POST /order`. It post an dummy order and returns OK.

Our goal is to to be able to get these following metrics from
all endpoints:

1. Request rate (per second)
2. Request duration (in millisecond)
3. Error rate (4xx or 5xx response)


### How to get, store and display the metrics data
Prometheus collect the data from our Sanic application by scraping `/metrics` endpoint.
So our step-by-step is:

1. Collect metrics from our application.
2. Expose the collected metrics via `/metrics` endpoint.
3. Add new job configuration for Prometheus.
4. Query the data on the grafana dashboard.

We will get into details for each step on the section below.

For the metrics collection, we will use the official
[Prometheus Python Client](https://github.com/prometheus/client_python)
to collect metrics from our Sanic application. Run the following command to
get the package:

    pip install -U prometheus_client

So in the next section, we will start collecting request rate from our Sanic app.


### Request Rate
In this section we are going to collect the request rate data and display the value
to the Grafana dashboard.

First of all, we need to understand what kind of metrics that we can store in
the Prometheus. Currently, there are 4 types of metric in the Prometheus
that we can use to represent our data:

1. [Counter](https://prometheus.io/docs/concepts/metric_types/#counter).
   A counter is a cumulative metric that represents a single numerical
   value that only ever goes up. A counter is typically used to count
   requests served, tasks completed, errors occurred, etc.
2. [Gauge](https://prometheus.io/docs/concepts/metric_types/#gauge).
   A gauge is a metric that represents a single numerical value that
   can arbitrarily go up and down.
3. [Histogram](https://prometheus.io/docs/concepts/metric_types/#histogram).
   A histogram samples observations (usually things like request durations
   or response sizes) and counts them in configurable buckets. It also
   provides a sum of all observed values.
4. [Summary](https://prometheus.io/docs/concepts/metric_types/#summary).
   Similar to a histogram, a summary samples observations (usually things
   like request durations and response sizes). While it also provides a
   total count of observations and a sum of all observed values, it
   calculates configurable quantiles over a sliding time window.

For request rate metric, we will use `Counter` metric type.

The first step that we do is import the prometheus client and initialize
our Counter metric:

```python
import prometheus_client as prometheus

# Initialize the metrics
counter = prometheus.Counter("sanic_requests_total",
                             "Track the total number of requests",
                             ["method", "endpoint"])
```

`"sanic_requests_total"` is the name of our metric, we must follow the
[Prometheus guideline](https://prometheus.io/docs/practices/naming/) for this.
There is a description and the label `["method", "endpoint"]` to helps us to
distinguish each request for which endpoint.

Since we want to track all requests on all endpoints, we can use
[middleware](http://sanic.readthedocs.io/en/latest/sanic/middleware.html)
to achieve this.

```python
# Track the total number of requests
@app.middleware('request')
async def track_requests(request):
    # Increase the value for each request
    # pylint: disable=E1101
    counter.labels(method=request.method,
                   endpoint=request.path).inc()
```

This middleware will increase our Counter value based on the `request.method`
(`GET`, `POST`, etc) and the `request.path` (`/`, `/products` etc).

So we already track all of the requests, the next step is to expose the
`/metrics` endpoint to be scraped by Prometheus.

```python
# Expose the metrics for prometheus
@app.get("/metrics")
async def metrics(request):
    output = prometheus.exposition.generate_latest().decode("utf-8")
    content_type = prometheus.exposition.CONTENT_TYPE_LATEST
    return response.text(body=output,
                         content_type=content_type)
```

So here is the full implementation:

```python

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
@app.middleware("request")
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

Now you can run your Sanic app and it will collect the metrics for each requests.
However it is not stored in the Prometheus yet. We need to tell the Prometheus
instance where to to scrap the metrics data. Add the following job definition
to the prometheus [config file](https://prometheus.io/docs/introduction/first_steps/#configuring-prometheus)
and restart your Prometheus instance:

```yaml
- job_name: sampleapp
  scrape_interval: 15s
  scrape_timeout: 10s
  metrics_path: /metrics
  scheme: http
  static_configs:
  - targets:
    - host.docker.internal:8080
```

I use `host.docker.internal` as the host of my Sanic app because
I run it on my local machine. My localhost is accessible inside docker
container using `host.docker.internal` as the host.

Access your prometheus instance [http://localhost:9090/graph](http://localhost:9090/graph)
and make sure the metrics data is available:

TODO: continue here

#### Questions

- Sometimes we restart or re-deploy our Sanic application, we may ask what happens when the process restarts and the counter is reset to 0?
  This is a common case, luckily the [rate()](https://prometheus.io/docs/prometheus/latest/querying/functions/#rate)
  function in Prometheus will automatically handle this for us. So it is okay if
  the Sanic application process is restarted and the value is resetted to zero,
  nothing bad will happen.
- The value of the counter is always increase, we may ask what happens when the value of the counter is overflowing?
  The prometheus client is using a
  [float value that protected by a mutex](https://github.com/prometheus/client_python/blob/master/prometheus_client/core.py#L315).
  When the value reach larger than `sys.float_info.max`, it will returns `+Inf` as the value.
  This will cause your graph displaying a zero flatline on the related timestamp. The current
  solution is to restart your sanic application. It depends on your traffic volumes and
  your deployment frequencies, this overflowing case may never happen.


Resources:
- [How does a Prometheus Counter work?](https://www.robustperception.io/how-does-a-prometheus-counter-work/)
