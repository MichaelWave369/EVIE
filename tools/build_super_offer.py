import os, requests, json

BASE = os.environ.get("EV_API_BASE", "http://127.0.0.1:18791")
KEY = os.environ.get("EV_API_KEY", "change-me-long-random")

topic = os.environ.get("EV_TOPIC", "Your first sellable capsule pack")
modules = ["ebooks","youtube","newsletter","stock","etsy","affiliate","pod","templates","microcourse","licensing","leadmagnet","directory","community","marketplace_assets","miniapp","extension","trend_miner","repurposer","offer_ladder","conversion_packager","pricing_optimizer","review_miner","support_macros"]

r = requests.post(f"{BASE}/v1/flywheel/offer", headers={"X-API-Key": KEY}, json={
    "topic": topic,
    "modules": modules,
    "price_cents": int(os.environ.get("EV_PRICE_CENTS", "2900")),
}, timeout=600)

print(r.status_code)
print(json.dumps(r.json(), indent=2))
