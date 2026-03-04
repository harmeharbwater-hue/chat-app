import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from app.api.auth import decode_access_token


router = APIRouter()

connections: Dict[int, Set[WebSocket]] = {}


async def _register_connection(user_id: int, websocket: WebSocket) -> None:
    if user_id not in connections:
        connections[user_id] = set()
    connections[user_id].add(websocket)


async def _unregister_connection(user_id: int, websocket: WebSocket) -> None:
    if user_id in connections:
        connections[user_id].discard(websocket)
        if not connections[user_id]:
            del connections[user_id]


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    token_data = decode_access_token(token)
    if token_data is None or token_data.user_id is None:
        await websocket.close(code=4401)
        return

    user_id = token_data.user_id
    await websocket.accept()
    await _register_connection(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "invalid_json"}))
                continue

            msg_type = payload.get("type")
            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            if msg_type == "message":
                to_user_id = payload.get("to_user_id")
                body = payload.get("body")
                if not isinstance(to_user_id, int) or not isinstance(body, str):
                    await websocket.send_text(json.dumps({"error": "invalid_payload"}))
                    continue

                # Echo back to sender
                outgoing = {
                    "type": "message",
                    "from_user_id": user_id,
                    "to_user_id": to_user_id,
                    "body": body,
                }
                await websocket.send_text(json.dumps(outgoing))

                # Forward to recipient if they are connected
                if to_user_id in connections:
                    for ws in list(connections[to_user_id]):
                        await ws.send_text(json.dumps(outgoing))
    except WebSocketDisconnect:
        await _unregister_connection(user_id, websocket)

