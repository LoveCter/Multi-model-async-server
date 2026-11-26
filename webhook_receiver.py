"""Tiny server for port 9000 that prints the webhook payloads sent by the worker."""
from fastapi import FastAPI, Request

app = FastAPI(title="Webhook receiver")


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    print("webhook received:", body)
    return {"ok": True}
