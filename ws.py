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

    async def connect(self, client):
        websocket, gameId, playerName = client
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, client):
        websocket, gameId, playerName = client
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, copyId: str):
        for connection in self.active_connections:
            
            await connection.send_text(message)


manager = ConnectionManager()

def canPut(game, player, card=None):
    
    if card:
        if game['cardSheet'][-1]['name'] != card['name'] and game['cardSheet'][-1]['type'] != card['type']:
            return False
    
    if player['que'] == False:
        return False
    
    res = False
    for cardOne in player['cards']:
        if game['cardSheet'][-1]['name'] == cardOne['name'] or game['cardSheet'][-1]['type'] == cardOne['type']:
            res = True
    
    return res       
 
def takeCard(game, player):
        
    for playerOne in game["players"]:
        if playerOne['name'] == player['name']:
            player['cards'].append(random.sample(game['cardStore'], k=1))
            game['cardStore'].remove(player['cards'][-1])
            return game
    
         

def passQue(game, playerName):
    players = game['players']
    num_players = len(players)

    # Find the index of the player with the given name
    current_index = next((i for i, p in enumerate(players) if p['name'] == playerName), None)

    if current_index is None:
        raise ValueError(f"No player found with name: {playerName}")

    # Reset all players' que to False
    for p in players:
        p['que'] = False

    # Find the next player who hasn't won
    for i in range(1, num_players):
        next_index = (current_index + i) % num_players
        next_player = players[next_index]

        if not next_player.get('won', False):
            next_player['que'] = True
            break
    
    if canPut(game, next_player) == False:
        game = takeCard(game, next_player)
        game = passQue(game, next_player['name'])
        
        
    return game


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
            await manager.broadcast(f"{playerName} is joined", copyId)
            return game


@app.put("/deal-game")
async def deal(copyId: str):
    
    for game in manager.active_games:
        if game["copyId"] == copyId:
            for player in game["players"]:
                player['cards'] = random.sample(game['cardStore'], k=game['cardsPerPlayer'])
                for pc in player['cards']:
                    game['cardStore'].remove(pc)
            await manager.broadcast(f"Cards have been dealed!", copyId)
            return game

@app.get("/game/{copyId}")
async def one(copyId: str):
    
    for game in manager.active_games:
        if game["copyId"] == copyId:
            return game

@app.put("/put-card")
async def put_card(card: dict, playerName: str, copyId: str):
    
    for game in manager.active_games:
        if game["copyId"] == copyId:
            
            for player in game["players"]:
                if player['name'] == playerName:
                    
                    if canPut(game, player) == False:
                        return game

                    if player['won'] == True:
                        raise HTTPException(400, "You are already won")
                    
                    if not card in player['cards']:
                        raise HTTPException(400, "You are cheating bro")
                    else:
                        player['cards'].remove(card)
                    
                    lastCard = game['cardSheet'][-1]
                    
                    if card['type'] == lastCard['type'] or card['value'] == lastCard['value']:
                        game['cardSheet'].append(card)      
                    else:
                        takenCard = random.choice(game['cardStore'])    
                        game['cardStore'].remove(takenCard)
                        
                    if len(player['cards']) == 0:        
                        player['won'] = True
                    
                    game["players"] = passQue(game, playerName)
                    await manager.broadcast(f"{playerName} put {card['name']} {card['type']}", copyId)
                    return game
                    
@app.delete("/terminate-game")
async def terminate(gameId: str):
    manager.active_games = [game for game in manager.active_games if game["copyId"] != gameId]
    await manager.broadcast(f"Game was terminated", gameId)
    return manager.active_games


@app.websocket("/ws/{gameId}/{clientName}")
async def websocket_endpoint(websocket: WebSocket, gameId: str, clientName: str):
    await manager.connect((websocket, gameId, clientName))
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", (websocket, gameId, clientName))
            await manager.broadcast(f"Client #{clientName} says: {data}", gameId)
    except WebSocketDisconnect:
        manager.disconnect((websocket, gameId, clientName))
        await manager.broadcast(f"Client #{clientName} left the game")