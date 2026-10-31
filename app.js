const $ = id => document.getElementById(id);
let socket=null, playerId=null, isHost=false, currentCode=null, currentState=null, answered=false, timerLoop=null;
const screens=["home","lobby","game","finished"];
function show(name){screens.forEach(s=>$(s).classList.toggle("hidden",s!==name))}
function error(id,msg){$(id).textContent=msg||""}
function connect(action){
  const name=$("playerName").value.trim();
  if(!name){error("homeError","Please enter your player name first.");$("playerName").focus();return}
  error("homeError","");
  if(socket) socket.close();
  const protocol=location.protocol==="https:"?"wss":"ws";
  socket=new WebSocket(`${protocol}://${location.host}/ws`);
  socket.onopen=()=>socket.send(JSON.stringify({action,name,code:$("roomCode").value.trim().toUpperCase()}));
  socket.onmessage=e=>handle(JSON.parse(e.data));
  socket.onerror=()=>error("homeError","Connection issue. Please refresh and try again.");
  socket.onclose=()=>{if(currentCode)error("lobbyError","Connection closed. Refresh to reconnect.");};
}
$("createBtn").onclick=()=>connect("create");
$("joinBtn").onclick=()=>{if($("roomCode").value.trim().length!==5){error("homeError","Enter the 5-character room code.");return}connect("join")};
$("roomCode").addEventListener("input",e=>e.target.value=e.target.value.toUpperCase().replace(/[^A-Z0-9]/g,""));
$("copyBtn").onclick=async()=>{try{await navigator.clipboard.writeText(currentCode);$("copyBtn").textContent="Copied!"}catch{$("copyBtn").textContent="Code: "+currentCode}setTimeout(()=>$("copyBtn").textContent="Copy code",1600)};
$("startBtn").onclick=()=>socket?.send(JSON.stringify({action:"start"}));
$("playAgain").onclick=()=>{currentCode=null;playerId=null;show("home");error("homeError","Create a new room to play again.")};
function handle(m){
 if(m.type==="error"){error(currentCode?"lobbyError":"homeError",m.message);return}
 if(m.type==="welcome"){playerId=m.playerId;currentCode=m.code;isHost=m.host;$("lobbyCode").textContent=m.code;show("lobby");return}
 if(m.type==="answer_received"){return}
 if(m.type==="reveal"){const correct=m.correct;const label=currentState?.choices?.[correct]||"";$("reveal").textContent="Correct answer: "+label;$("reveal").classList.remove("hidden");return}
 if(m.type==="state"){currentState=m;render(m)}
}
function render(s){
 if(s.status==="lobby"){
  show("lobby");$("lobbyCode").textContent=s.code;$("playerCount").textContent=`${s.players.length} / 6`;
  $("players").innerHTML=s.players.map((p,i)=>`<div class="player"><div class="player-name"><span class="avatar">${esc(p.name[0].toUpperCase())}</span>${esc(p.name)} ${p.id===playerId?'<span class="you">YOU</span>':''}</div><span>${p.id===s.hostId?"👑 HOST":p.connected?"● READY":"○ RECONNECTING"}</span></div>`).join("");
  $("startBtn").classList.toggle("hidden",!isHost);$("hostHint").textContent=isHost?"You're the host. Start when at least 2 players have joined.":"Waiting for the host to start the game…";
 }else if(s.status==="question"){
  show("game");answered=false;$("reveal").classList.add("hidden");$("roundLabel").textContent=`QUESTION ${s.round+1} / ${s.totalRounds}`;$("questionText").textContent=s.question;$("answeredCount").textContent=`${s.answered} answered`;
  $("choices").innerHTML=s.choices.map((c,i)=>`<button class="choice" data-choice="${i}"><span class="letter">${"ABCD"[i]}</span>${esc(c)}</button>`).join("");
  document.querySelectorAll(".choice").forEach(b=>b.onclick=()=>submitAnswer(Number(b.dataset.choice)));
  startTimer(s.deadline);renderScores(s.players);
 }else if(s.status==="reveal"){
  show("game");renderScores(s.players);document.querySelectorAll(".choice").forEach(b=>b.disabled=true);
 }else if(s.status==="finished"){
  show("finished");renderScores(s.players,"finalPlayers");const sorted=[...s.players].sort((a,b)=>b.score-a.score);const winner=sorted[0];$("winnerBox").innerHTML=`<div class="crown">👑</div><small>QUIZ CLASH CHAMPION</small><strong>${esc(winner?.name||"No winner")}</strong><small>${winner?.score||0} points</small>`;
 }
}
function submitAnswer(choice){if(answered)return;answered=true;socket.send(JSON.stringify({action:"answer",choice}));document.querySelectorAll(".choice").forEach(b=>b.disabled=true);$("answerStatus").textContent="Answer submitted ✓"}
function startTimer(deadline){if(timerLoop)clearInterval(timerLoop);const tick=()=>{const left=Math.max(0,deadline-Date.now()/1000);$("timer").textContent=Math.ceil(left);$("progressBar").style.width=(left/15*100)+"%";if(left<=0)clearInterval(timerLoop)};tick();timerLoop=setInterval(tick,100)}
function renderScores(players,target="gamePlayers"){const sorted=[...players].sort((a,b)=>b.score-a.score);$(target).innerHTML=sorted.map((p,i)=>`<div class="score-row"><div class="score-name"><span class="rank">${i+1}</span><span class="avatar">${esc(p.name[0].toUpperCase())}</span>${esc(p.name)} ${p.id===playerId?'<span class="you">YOU</span>':''}</div><span class="score-points">${p.score.toLocaleString()}</span></div>`).join("")}
function esc(v){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
