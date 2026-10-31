import asyncio, json, random, string, time
from pathlib import Path
from typing import Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
app = FastAPI(title="Quiz Clash")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

QUESTIONS = [
    {"q":"Which planet is known as the Red Planet?","choices":["Venus","Mars","Jupiter","Mercury"],"answer":1},
    {"q":"What does CPU stand for?","choices":["Central Processing Unit","Computer Personal Utility","Core Program Unit","Central Power User"],"answer":0},
    {"q":"Which language is primarily used to style web pages?","choices":["Python","HTML","CSS","SQL"],"answer":2},
    {"q":"What is the capital of Japan?","choices":["Seoul","Beijing","Bangkok","Tokyo"],"answer":3},
    {"q":"Which AWS service provides virtual servers?","choices":["S3","EC2","Lambda","Route 53"],"answer":1},
    {"q":"How many bits are in a byte?","choices":["4","8","16","32"],"answer":1},
    {"q":"Which data structure follows FIFO?","choices":["Stack","Tree","Queue","Graph"],"answer":2},
    {"q":"What does HTTP stand for?","choices":["HyperText Transfer Protocol","High Transfer Text Process","Hyperlink Terminal Transfer Program","Host Text Transport Protocol"],"answer":0},
    {"q":"Which ocean is the largest?","choices":["Atlantic","Indian","Arctic","Pacific"],"answer":3},
    {"q":"What is 12 × 8?","choices":["84","96","108","88"],"answer":1},
    {"q":"Which command lists files in Linux?","choices":["pwd","cd","ls","mkdir"],"answer":2},
    {"q":"Which one is a version control system?","choices":["Docker","Git","Nginx","Kubernetes"],"answer":1},
]

rooms: Dict[str, dict] = {}
locks: Dict[str, asyncio.Lock] = {}

def room_code():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(alphabet, k=5))
        if code not in rooms:
            return code

def public_players(room):
    return [{"id": p["id"], "name": p["name"], "score": p["score"],
             "connected": p["ws"] is not None} for p in room["players"].values()]

def snapshot(room):
    state = {"type":"state", "code":room["code"], "hostId":room["host"],
             "players":public_players(room), "status":room["status"],
             "round":room["round"], "totalRounds":room["total_rounds"]}
    if room["status"] == "question":
        q = room["questions"][room["round"]]
        state.update({"question":q["q"], "choices":q["choices"],
                      "deadline":room["deadline"], "answered":len(room["answers"])})
    elif room["status"] == "finished":
        state["winner"] = max(room["players"].values(), key=lambda p:p["score"])["id"] if room["players"] else None
    return state

async def send_room(room):
    data = json.dumps(snapshot(room))
    stale = []
    for p in room["players"].values():
        ws = p["ws"]
        if ws:
            try: await ws.send_text(data)
            except Exception: stale.append(p["id"])
    for pid in stale:
        room["players"][pid]["ws"] = None

async def broadcast(room, payload):
    data = json.dumps(payload)
    for p in list(room["players"].values()):
        if p["ws"]:
            try: await p["ws"].send_text(data)
            except Exception: p["ws"] = None

async def next_question(room):
    if room["round"] + 1 >= room["total_rounds"]:
        room["status"] = "finished"
        await send_room(room)
        return
    room["round"] += 1
    room["answers"] = {}
    room["status"] = "question"
    room["deadline"] = time.time() + room["question_seconds"]
    await send_room(room)
    asyncio.create_task(question_timeout(room["code"], room["round"], room["deadline"]))

async def question_timeout(code, round_no, deadline):
    await asyncio.sleep(max(0, deadline - time.time()))
    room = rooms.get(code)
    if not room: return
    async with locks[code]:
        if room["status"] == "question" and room["round"] == round_no and room["deadline"] == deadline:
            await broadcast(room, {"type":"reveal", "correct":room["questions"][round_no]["answer"],
                                    "answers":len(room["answers"])})
            room["status"] = "reveal"
            await send_room(room)
            await asyncio.sleep(2.5)
            if rooms.get(code) is room and room["status"] == "reveal":
                await next_question(room)

@app.get("/")
async def index():
    return FileResponse(BASE / "static" / "index.html")

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    code = None
    player_id = None
    try:
        first = json.loads(await ws.receive_text())
        action = first.get("action")
        name = str(first.get("name","Player")).strip()[:18] or "Player"
        if action == "create":
            code = room_code()
            player_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
            rooms[code] = {"code":code, "host":player_id, "players":{},
                           "status":"lobby", "round":-1, "total_rounds":8,
                           "question_seconds":15, "deadline":None, "answers":{},
                           "questions":random.sample(QUESTIONS, 8)}
            locks[code] = asyncio.Lock()
        elif action == "join":
            code = str(first.get("code","")).upper().strip()
            room = rooms.get(code)
            if not room: await ws.send_json({"type":"error","message":"Room not found. Check the code and try again."}); return
            if room["status"] != "lobby": await ws.send_json({"type":"error","message":"This game has already started."}); return
            if len(room["players"]) >= 6: await ws.send_json({"type":"error","message":"This room is full (6 players)."}); return
            player_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        else:
            await ws.send_json({"type":"error","message":"Unknown action."}); return

        room = rooms[code]
        if len(room["players"]) >= 6:
            await ws.send_json({"type":"error","message":"This room is full (6 players)."}); return
        room["players"][player_id] = {"id":player_id, "name":name, "score":0, "ws":ws}
        await ws.send_json({"type":"welcome","playerId":player_id,"code":code,"host":player_id == room["host"]})
        await send_room(room)

        while True:
            msg = json.loads(await ws.receive_text())
            async with locks[code]:
                room = rooms.get(code)
                if not room or player_id not in room["players"]: break
                if msg.get("action") == "start":
                    if player_id != room["host"] or room["status"] != "lobby": continue
                    if len(room["players"]) < 2:
                        await ws.send_json({"type":"error","message":"At least 2 players are needed to start."}); continue
                    await next_question(room)
                elif msg.get("action") == "answer":
                    if room["status"] != "question" or player_id in room["answers"]: continue
                    if time.time() > room["deadline"]: continue
                    choice = msg.get("choice")
                    if not isinstance(choice, int) or choice < 0 or choice > 3: continue
                    correct = room["questions"][room["round"]]["answer"]
                    is_correct = choice == correct
                    room["answers"][player_id] = choice
                    if is_correct:
                        remaining = max(0, room["deadline"] - time.time())
                        room["players"][player_id]["score"] += 500 + int(remaining * 30)
                    await broadcast(room, {"type":"answer_received","playerId":player_id})
                    if len(room["answers"]) >= len(room["players"]):
                        await broadcast(room, {"type":"reveal","correct":correct,"answers":len(room["answers"])})
                        room["status"] = "reveal"
                        await send_room(room)
                        asyncio.create_task(advance_after_reveal(code, room["round"]))
                    else:
                        await send_room(room)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if code and player_id and code in rooms:
            room = rooms[code]
            if player_id in room["players"]:
                room["players"][player_id]["ws"] = None
                await send_room(room)

async def advance_after_reveal(code, round_no):
    await asyncio.sleep(2.5)
    room = rooms.get(code)
    if not room: return
    async with locks[code]:
        if room["status"] == "reveal" and room["round"] == round_no:
            await next_question(room)
