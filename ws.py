from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import random
import uuid

card_types = ['diamonds', 'clubs', 'hearts', 'spades']
card_units = ['6', '7', '8', '9', '10', 'jack', 'queen', 'king', 'ace']
all_cards = [{"name": name, "type": tip, "value": index + 6, "img": f"/static/cards/{name}_of_{tip}.png"} 
             for index, name in enumerate(card_units) 
             for tip in card_types]


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"))
# CORS setup (if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
with open("game.html") as f:
    html = str(f.read())


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.active_games: list[object] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def get():
    return HTMLResponse(html)

@app.post("/create-game")
async def create(playerName: str, cardsPerPlayer: int):
    waitCards = all_cards
    firstCard = random.choice(all_cards)
    waitCards.remove(firstCard)
    newGame = {
        "copyId": str(uuid.uuid4())[:6],
        "adminName": playerName,
        "cardStore": waitCards,
        "cardsPerPlayer": cardsPerPlayer,
        "cardSheet": [firstCard],
        "players": [{
            "name": playerName, 
            "cards": [],
            "won": False,
            "que": True
        }]
    }
    manager.active_games.append(newGame)
    
    return newGame

@app.post("/join-game")
async def join(playerName: str, copyId: str):
    
    for game in manager.active_games:
        if game["copyId"] == copyId:
            for player in game["players"]:
                if player["name"] == playerName:
                    return game
                continue
            
            game["players"].append({
                "name": playerName, 
                "cards": [],
                "won": False,
                "que": False
            })
   
            return game


@app.put("/deal-game")
async def deal(copyId: str):
    
    for game in manager.active_games:
        if game["copyId"] == copyId:
            for player in game["players"]:
               player['cards'] = random.sample(game['cardStore'], k=game['cardsPerPlayer'])
               for pc in player['cards']:
                try:
                    game['cardStore'].remove(pc)
                except Exception as e:
                    print(pc)
   
            return game

@app.put("/put-card")
async def put_card(card: dict, playerName: str, copyId: str):
    
    for game in manager.active_games:
        if game["copyId"] == copyId:
            for player in game["players"]:
                if player['name'] == playerName:

                    if player['won'] == True:
                        raise HTTPException(400, "You are already won")
                    
                    if not player['cards'].remove(card):
                        raise HTTPException(400, "You are cheating bro")
                    
                    lastCard = game['cardSheet'][-1]
                    
                    if card['type'] == lastCard['type'] or card['value'] == lastCard['value']:
                        game['cardSheet'].append(card)      
                    else:
                        takenCard = random.choice(game['cardStore'])    
                        game['cardStore'].remove(takenCard)
                        
                    if len(player['cards']) == 0:        
                        player['won'] = True
                        
                    return player
                    
@app.delete("/terminate-game")
async def terminate(gameId: str):
    manager.active_games = [game for game in manager.active_games if game["copyId"] != gameId]
    return manager.active_games


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")