let currentConcern = "";
let currentAnalysis = {};

async function analyze(){
  const text = document.getElementById("concern").value.trim();
  if(!text){ alert("Please describe your concern first."); return; }
  currentConcern = text;
  const btn = document.querySelector(".primary");
  btn.disabled = true; btn.innerHTML = "Understanding…";
  try{
    const r = await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text})});
    const data = await r.json();
    if(data.error) throw new Error(data.error);
    currentAnalysis = data.analysis;
    document.getElementById("category").textContent = currentAnalysis.category || "Care navigation";
    document.getElementById("urgency").textContent = currentAnalysis.urgency || "Routine";
    document.getElementById("note").textContent = currentAnalysis.note || currentAnalysis.summary || "";
    document.getElementById("sourceBadge").textContent = data.source === "gemini" ? "GEMINI AI" : "NAVIGATION DEMO";
    document.getElementById("result").classList.remove("hidden");
    await loadMatches();
    await loadChecklist();

    requestUserLocation();
    document.getElementById("result").scrollIntoView({behavior:"smooth"});
  }catch(e){alert("Something went wrong: "+e.message)}
  finally{btn.disabled=false;btn.innerHTML="Find my care path <span>→</span>"}
}

async function loadMatches(coords=null){
  const body = { concern: currentConcern };

  if(coords){
    body.lat = coords.latitude;
    body.lon = coords.longitude;
  }

  const r = await fetch("/api/match", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });

  const list = await r.json();

  document.getElementById("facilities").innerHTML = list.map(f => `
    <article class="facility">
      <span class="status">${f.status}</span>

      <h3>${f.name}</h3>

      <div class="type">
        ${f.type} • ${f.area}
      </div>

      <p>
        <b>Services:</b> ${f.services}
      </p>

      <p>
        <b>Timings:</b> ${f.timings}
      </p>

      <p>
        <b>Accessibility:</b> ${f.accessibility}
      </p>

      <div class="tags">
        <span class="tag">🗣 ${f.languages}</span>

        ${
          f.distance_km !== null
          ? `<span class="tag">📍 ${f.distance_km} km</span>`
          : ""
        }

        <span class="tag">Public facility</span>
      </div>
    </article>
  `).join("");

  renderPhcMap(list, coords);
}

function useLocation(){
  if(!navigator.geolocation){alert("Location is not supported by this browser.");return}
  navigator.geolocation.getCurrentPosition(async p=>{
    await loadMatches(p.coords);
  },()=>alert("Location permission was not granted. Showing general recommendations instead."));
}

async function loadChecklist(){
  const r=await fetch("/api/checklist",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({category:currentAnalysis.category})});
  const d=await r.json();
  document.getElementById("docs").innerHTML=d.documents.map(x=>`<li>☐ ${x}</li>`).join("");
  document.getElementById("questions").innerHTML=d.questions.map(x=>`<li>• ${x}</li>`).join("");
}

function startVoice(){
  const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SpeechRecognition){document.getElementById("voiceStatus").textContent="Voice input is not supported in this browser. Try Chrome.";return}
  const r=new SpeechRecognition();
  r.lang=document.documentElement.lang==="hi"?"hi-IN":"en-IN";
  r.interimResults=false;
  document.getElementById("voiceStatus").textContent="Listening…";
  r.onresult=e=>{document.getElementById("concern").value=e.results[0][0].transcript;document.getElementById("voiceStatus").textContent="Voice captured ✓"};
  r.onerror=()=>document.getElementById("voiceStatus").textContent="Could not capture voice. Please try again.";
  r.onend=()=>{if(document.getElementById("voiceStatus").textContent==="Listening…")document.getElementById("voiceStatus").textContent=""};
  r.start();
}
function toggleLang(){
  alert("Prototype multilingual UI hook: voice recognition supports English (India) and the backend is ready for localized AI responses. Full Hindi UI translation can be added without changing the core architecture.");
}

let phcMap = null;

function renderPhcMap(facilities, userCoords=null){

  const container = document.getElementById("phcMap");

  if(!container){
    return;
  }

  if(typeof L === "undefined"){
    console.error("Leaflet was not loaded.");
    return;
  }

  // Remove previous map instance
  if(phcMap){
    phcMap.remove();
    phcMap = null;
  }

  let centerLat = 28.6139;
  let centerLon = 77.2090;
  let zoom = 11;

  // If we have the user's location,
  // center the map around them.
  if(userCoords){
    centerLat = userCoords.latitude;
    centerLon = userCoords.longitude;
    zoom = 12;
  }

  phcMap = L.map("phcMap").setView(
    [centerLat, centerLon],
    zoom
  );

  L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19
    }
  ).addTo(phcMap);

  // User location marker
  if(userCoords){

    L.marker([
      userCoords.latitude,
      userCoords.longitude
    ])
    .addTo(phcMap)
    .bindPopup("<b>You are here</b>")
    .openPopup();
  }

  // Facility markers
  facilities.forEach((f, index) => {

    if(f.lat === null || f.lon === null){
      return;
    }

    const distanceText =
      f.distance_km !== null
      ? `<br><b>Distance:</b> ${f.distance_km} km`
      : "";

    const popup = `
      <div>
        <b>${index + 1}. ${f.name}</b>
        <br>
        ${f.type}
        <br>
        <b>Area:</b> ${f.area}
        ${distanceText}
        <br>
        <b>Status:</b> ${f.status}
      </div>
    `;

    L.marker([
      f.lat,
      f.lon
    ])
    .addTo(phcMap)
    .bindPopup(popup);
  });

  // Make the map fit all visible markers
  const points = [];

  if(userCoords){
    points.push([
      userCoords.latitude,
      userCoords.longitude
    ]);
  }

  facilities.forEach(f => {
    if(f.lat !== null && f.lon !== null){
      points.push([
        f.lat,
        f.lon
      ]);
    }
  });

  if(points.length > 1){
    phcMap.fitBounds(points, {
      padding: [40, 40]
    });
  }
}

function requestUserLocation(){

  if(!navigator.geolocation){
    console.log("Geolocation is not supported.");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    async position => {

      const coords = position.coords;

      console.log(
        "User location:",
        coords.latitude,
        coords.longitude
      );

      await loadMatches(coords);
    },

    error => {

      console.log(
        "Location unavailable:",
        error.message
      );

      // Keep the general recommendations already loaded.
    },

    {
      enableHighAccuracy: true,
      timeout: 8000,
      maximumAge: 300000
    }
  );
}
