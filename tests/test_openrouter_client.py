import json
import responses
import os
import time
from importlib import reload

@responses.activate
def test_chat_once_ok_headers_and_body(openrouter_module, monkeypatch):
    chat_once = openrouter_module.chat_once
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {"id": "cmpL1", "choices": [{"message": {"content": "OK"}}]}
    responses.add(responses.POST, url, json=payload, status=200)

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    openrouter_module = reload(openrouter_module) # перечитает ключ
    chat_once = openrouter_module.chat_once

    text, ms = chat_once(
        messages=[{"role": "user", "content": "ping"}],
        model="mistralai/mistral-small-24b-instruct-2501:free",
        temperature=0.2,
        max_tokens=32,
        timeout_s=5,
    )
    assert text == "OK"
    # проверяем отправленное тело
    sent = json.loads(responses.calls[0].request.body.decode())
    assert sent["model"].endswith(":free")
    assert sent["messages"][0]["role"] == "user"
    assert "temperature" in sent and "max_tokens" in sent
    # и заголовки
    hdrs = responses.calls[0].request.headers
    assert hdrs["Content-Type"] == "application/json"
    assert hdrs["Authorization"] == "Bearer test-key"

