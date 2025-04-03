var client_id = Date.now();
httpURL = "http://localhost:8000";
document.querySelector("#ws-id").textContent = client_id;
var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
ws.onmessage = function (event) {
  var messages = document.getElementById("messages");
  var message = document.createElement("li");
  var content = document.createTextNode(event.data);
  message.appendChild(content);
  messages.appendChild(message);
};

function post(url, data = {}) {
  return fetch(`${httpURL}/${url}`, {
    method: "POST",
    data: data,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  }).then((res) => res.json());
}
function put(url) {
  return fetch(`${httpURL}/${url}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  }).then((res) => res.json());
}

function get(url) {
  return fetch(`${httpURL}/${url}`).then((res) => res.json());
}

function setData(game) {
  let playerName = localStorage.getItem("playerName");
  document.getElementById("newGameCard").style.display = "none";
  document.getElementById("activeGameCard").style.display = "block";
  document.getElementById("copyId").innerHTML = game.copyId;
  document.getElementById("players").innerHTML = "";

  game.players.forEach((player) => {
    if (player.name !== playerName) {
      document.getElementById("players").innerHTML += `
    <div class="col-md-3">
        <div class="card p-2 ${player.que && 'bg-warning'}">
            <h3>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
 <path d="M12 15C8.8299 15 6.01077 16.5306 4.21597 18.906C3.82968 19.4172 3.63653 19.6728 3.64285 20.0183C3.64773 20.2852 3.81533 20.6219 4.02534 20.7867C4.29716 21 4.67384 21 5.4272 21H18.5727C19.3261 21 19.7028 21 19.9746 20.7867C20.1846 20.6219 20.3522 20.2852 20.3571 20.0183C20.3634 19.6728 20.1703 19.4172 19.784 18.906C17.9892 16.5306 15.17 15 12 15Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
 <path d="M12 12C14.4853 12 16.5 9.98528 16.5 7.5C16.5 5.01472 14.4853 3 12 3C9.51469 3 7.49997 5.01472 7.49997 7.5C7.49997 9.98528 9.51469 12 12 12Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
 </svg>
 ${player.name}
 </h3>
        </div>
    </div>
    `;
    }else{
        player.que && document.getElementById("myCards").classList.add("bg-warning")
    }
  });

  document
    .getElementById("openCard")
    .setAttribute("src", game.cardSheet[0].img);

  game.players.forEach((player) => {
    if (player.name == playerName) {
      if (player.cards.length > 0) {
        document.getElementById("myCards").innerHTML = "";
        player.cards.forEach((card) => {
          document.getElementById("myCards").innerHTML += `
           <img 
            style="transition:0.3s;cursor:pointer"
            onmouseover="this.style.marginTop='-10px'" 
            onmouseout="this.style.marginTop='0px'" 
            width="150" 
            src="${card.img}" 
            alt="My Card">
            `;
        });
      }
    }
  });
}

function sendMessage(event) {
  var input = document.getElementById("messageText");
  ws.send(input.value);
  input.value = "";
  event.preventDefault();
}

function startGame() {
  let playerName = document.getElementById("playerName").value;
  localStorage.setItem("playerName", playerName);

  post(
    "create-game?playerName=" +
      playerName +
      "&cardsPerPlayer=" +
      document.getElementById("cardsPerPlayer").value
  ).then((data) => {
    localStorage.setItem("gameId", data.copyId);
    setData(data);
  });
}

function joinGame() {
  let playerName2 = document.getElementById("playerName2").value;
  let gameId = document.getElementById("gameId").value;

  localStorage.setItem("playerName", playerName2);
  localStorage.setItem("gameId", gameId);

  post("join-game?playerName=" + playerName2 + "&copyId=" + gameId).then(
    (data) => {
      setData(data);
    }
  );
}

function dealGame() {
  put("deal-game?copyId=" + localStorage.getItem("gameId")).then((data) => {
    setData(data);
  });
}
