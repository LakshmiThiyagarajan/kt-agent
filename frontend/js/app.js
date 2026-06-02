const API_BASE = "http://127.0.0.1:8000/api/v1";
const state = {
  employeeId: null, name: null, email: null,
  sessionId: null, isLoggedIn: false,
  profileComplete: false, selectedProject: null
};
const $ = (sel, ctx=document) => ctx.querySelector(sel);
const $$ = (sel, ctx=document) => [...ctx.querySelectorAll(sel)];
const PROTECTED = ["chat", "upload", "profile"];

function showPanel(name){
  $$(".panel").forEach(p => p.classList.remove("active"));
  $$(".nav-item").forEach(n => n.classList.remove("active"));
  $(`#panel-${name}`)?.classList.add("active");
  $(`[data-panel="${name}"]`)?.classList.add("active");
}

function toast(message, type="info"){
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  $("#toast-container").appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function navigateTo(name){
  if(PROTECTED.includes(name) && !state.isLoggedIn){
    toast("Please log in first.", "error");
    showPanel("login");
    return;
  }
  // Block navigation until profile is complete (setup panel itself is allowed)
  if(PROTECTED.includes(name) && !state.profileComplete){
    showPanel("setup");
    toast("Please complete your profile first.", "error");
    return;
  }
  showPanel(name);
  if(name === "profile") loadProfilePanel();
}

function saveSession(){
  localStorage.setItem("kt_session", JSON.stringify({
    employeeId: state.employeeId, name: state.name,
    email: state.email, sessionId: state.sessionId,
    profileComplete: state.profileComplete
  }));
}

function loadSession(){
  try{
    const raw = localStorage.getItem("kt_session");
    if(!raw) return false;
    const s = JSON.parse(raw);
    if(!s.employeeId) return false;
    state.employeeId = s.employeeId; state.name = s.name;
    state.email = s.email; state.sessionId = s.sessionId;
    state.isLoggedIn = true;
    state.profileComplete = s.profileComplete || false;
    return true;
  }catch{ return false; }
}

function clearSession(){
  localStorage.removeItem("kt_session");
  state.employeeId = null; state.name = null;
  state.email = null; state.sessionId = null;
  state.isLoggedIn = false; state.profileComplete = false;
  state.selectedProject = null;
}

function showAuthNav(loggedIn){
  $("#nav-login").style.display  = loggedIn ? "none" : "flex";
  $("#nav-chat").style.display   = loggedIn ? "flex" : "none";
  $("#nav-upload").style.display = loggedIn ? "flex" : "none";
  $("#nav-profile").style.display= loggedIn ? "flex" : "none";
  $("#nav-logout").style.display = loggedIn ? "flex" : "none";
}

function updateSidebarProfile(p=null){
  $("#sidebar-name").textContent = p?.name || state.name || "—";
  $("#sidebar-role").textContent = p?.role || "—";
  // Project in sidebar is driven by chat selection, not profile
}

function updateSidebarProject(){
  $("#sidebar-project").textContent = state.selectedProject
    ? `📁 ${state.selectedProject}`
    : "No project selected";
}

async function apiFetch(path, options={}){
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {"Content-Type": "application/json", ...options.headers}, ...options
  });
  if(!res.ok){
    const err = await res.json().catch(() => ({detail: res.statusText}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

async function login(){
  const username = $("#login-username").value.trim();
  const password = $("#login-password").value.trim();
  if(!username || !password){ toast("Enter username and password.", "error"); return; }
  const btn = $("#login-btn");
  btn.disabled = true; btn.textContent = "Signing in…";
  try{
    const data = await apiFetch("/auth/login", {
      method: "POST", body: JSON.stringify({username, password})
    });
    state.employeeId = data.employee_id; state.name = data.name;
    state.email = data.email; state.isLoggedIn = true;
    showAuthNav(true);
    updateSidebarProfile({name: data.name});
    toast(`Welcome, ${data.name}!`, "success");
    if(!data.profile_complete){
      // New user — go to dedicated setup panel
      state.profileComplete = false;
      saveSession();
      showPanel("setup");
    }else{
      state.profileComplete = true;
      saveSession();
      try{ const p = await apiFetch(`/profile/${state.employeeId}`); updateSidebarProfile(p); }catch(_){}
      navigateTo("chat");
    }
  }catch(err){ toast(err.message, "error"); }
  finally{ btn.disabled = false; btn.textContent = "Sign In →"; }
}

function logout(){
  clearSession();
  showAuthNav(false);
  updateSidebarProfile({name: "Not logged in"});
  $("#sidebar-role").textContent = "—";
  updateSidebarProject();
  $$(".project-btn").forEach(b => b.classList.remove("active"));
  const msgs = $("#chat-messages");
  while(msgs.children.length > 2) msgs.removeChild(msgs.lastChild);
  showPanel("login");
  toast("Logged out.", "info");
}

async function submitProfileSetup(){
  const role = $("#setup-role").value;
  const experience = $("#setup-experience").value;
  if(!role || !experience){
    toast("Please fill in all fields.", "error");
    return;
  }
  const btn = $("#setup-submit-btn");
  btn.disabled = true; btn.textContent = "Saving…";
  const payload = {
    employee_id: state.employeeId, name: state.name,
    email: state.email, role, experience_level: experience
  };
  try{
    try{
      await apiFetch("/profile", { method: "POST", body: JSON.stringify(payload) });
    }catch(err){
      // Profile already seeded — update instead
      if(err.message.toLowerCase().includes("already exists")){
        await apiFetch(`/profile/${state.employeeId}`, {
          method: "PATCH", body: JSON.stringify({ role, experience_level: experience })
        });
      } else { throw err; }
    }
    state.profileComplete = true;
    saveSession();
    updateSidebarProfile({name: state.name, role});
    toast("Profile saved! Let's get started.", "success");
    navigateTo("chat");
  }catch(err){ toast(`Error: ${err.message}`, "error"); }
  finally{ btn.disabled = false; btn.textContent = "Save and Continue"; }
}

// ── Markdown + messages ───────────────────────────────────────────────────────

function renderMarkdown(text){
  return text
    .replace(/^## (.+)$/gm,"<h2>$1</h2>")
    .replace(/^### (.+)$/gm,"<h3>$1</h3>")
    .replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>")
    .replace(/`(.+?)`/g,"<code>$1</code>")
    .replace(/^> (.+)$/gm,"<blockquote>$1</blockquote>")
    .replace(/^---$/gm,"<hr>")
    .replace(/^\d+\. (.+)$/gm,"<li>$1</li>")
    .replace(/^[-*•🔴🟡🟢] (.+)$/gm,"<li>$1</li>")
    .replace(/(<li>[\s\S]*?<\/li>)/g,s=>`<ul>${s}</ul>`)
    .replace(/\n\n/g,"</p><p>")
    .replace(/\n/g,"<br>");
}

function escapeHtml(s){
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function addMessage(role, content, meta={}){
  const wrap = document.createElement("div");
  wrap.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.innerHTML = role === "assistant" ? renderMarkdown(content) : escapeHtml(content);
  wrap.appendChild(bubble);
  if(role === "assistant" && meta.intent){
    const metaDiv = document.createElement("div");
    metaDiv.className = "message-meta";
    const it = document.createElement("span");
    it.className = "intent-tag"; it.textContent = meta.intent;
    metaDiv.appendChild(it);
    if(meta.groundedness_score !== undefined){
      const score = meta.groundedness_score;
      const st = document.createElement("span");
      st.className = `score-tag ${score < 0.6 ? "fail" : score < 0.8 ? "low" : ""}`;
      st.textContent = `⚡ ${Math.round(score * 100)}% grounded`;
      metaDiv.appendChild(st);
    }
    if(meta.planning_used){
      const pt = document.createElement("span");
      pt.className = "intent-tag"; pt.textContent = "🗺 planning";
      metaDiv.appendChild(pt);
    }
    wrap.appendChild(metaDiv);
    if(meta.sources?.length){
      const src = document.createElement("div");
      src.className = "sources";
      src.innerHTML = "📄 " + meta.sources.slice(0,4).map(s=>`<span class="source-chip">${s}</span>`).join("");
      wrap.appendChild(src);
    }
  }
  const msgs = $("#chat-messages");
  msgs.appendChild(wrap);
  msgs.scrollTop = msgs.scrollHeight;
  return wrap;
}

function showTyping(){
  const el = document.createElement("div");
  el.className = "message assistant typing-indicator"; el.id = "typing";
  el.innerHTML = `<div class="message-bubble"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>`;
  $("#chat-messages").appendChild(el);
  $("#chat-messages").scrollTop = 9999;
}
function hideTyping(){ $("#typing")?.remove(); }

// ── Chat ──────────────────────────────────────────────────────────────────────

async function sendMessage(){
  if(!state.isLoggedIn){ toast("Please log in first.", "error"); return; }
  const input = $("#chat-input");
  const message = input.value.trim();
  if(!message) return;
  input.value = ""; input.style.height = "auto";
  $("#send-btn").disabled = true;
  addMessage("user", message); showTyping();
  try{
    const data = await apiFetch("/chat", {
      method: "POST", body: JSON.stringify({
        employee_id: state.employeeId,
        message,
        session_id: state.sessionId,
        selected_project: state.selectedProject || null,
      })
    });
    state.sessionId = data.session_id; saveSession();
    $("#session-badge").textContent = `Session: ${data.session_id.slice(0,8)}`;
    hideTyping();
    addMessage("assistant", data.answer, {
      intent: data.intent, groundedness_score: data.groundedness_score,
      sources: data.sources, planning_used: data.planning_used
    });
  }catch(err){
    hideTyping();
    addMessage("assistant", `⚠️ Error: ${err.message}`);
    toast(err.message, "error");
  }finally{ $("#send-btn").disabled = false; input.focus(); }
}

// ── Upload ────────────────────────────────────────────────────────────────────

const FILE_ICONS = {pdf:"PDF",docx:"DOC",txt:"TXT",md:"MD",png:"IMG",jpg:"IMG",jpeg:"IMG",webp:"IMG",gif:"IMG",mp3:"AUD",mp4:"AUD",m4a:"AUD",wav:"AUD",webm:"AUD",ogg:"AUD"};
let selectedFiles = [];
let isUploading = false;

function setupDropZone(){
  const zone = $("#drop-zone"), input = $("#fileInput");
  zone.addEventListener("click", () => input.click());
  input.addEventListener("change", () => { if(input.files.length) addFiles(input.files); input.value=""; });
  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("dragover"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", e => {
    e.preventDefault(); zone.classList.remove("dragover");
    if(e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  });
}

function addFiles(fileList){
  Array.from(fileList).forEach(file => {
    if(!selectedFiles.find(f => f.name === file.name && f.size === file.size))
      selectedFiles.push(file);
  });
  renderFileList();
}

function removeFile(index){
  if(isUploading) return;
  selectedFiles.splice(index, 1);
  renderFileList();
}

function clearFiles(){
  if(isUploading) return;
  selectedFiles = [];
  renderFileList();
  $("#upload-summary").style.display = "none";
}

function fileSize(bytes){
  return bytes < 1024*1024
    ? `${(bytes/1024).toFixed(1)} KB`
    : `${(bytes/1024/1024).toFixed(1)} MB`;
}

function renderFileList(){
  const list = $("#file-list");
  const btn = $("#upload-btn");
  if(selectedFiles.length === 0){
    list.style.display = "none";
    btn.disabled = true;
    btn.textContent = "Upload All";
    return;
  }
  list.style.display = "block";
  btn.disabled = false;
  btn.textContent = `Upload All (${selectedFiles.length} file${selectedFiles.length>1?"s":""})`;

  list.innerHTML = `
    <div class="file-list-header">
      <span>${selectedFiles.length} file${selectedFiles.length>1?"s":""} selected</span>
      <button class="clear-all-btn" onclick="clearFiles()">Clear all</button>
    </div>
    ${selectedFiles.map((f,i) => {
      const ext = f.name.split(".").pop().toLowerCase();
      const badge = FILE_ICONS[ext] || "FILE";
      return `<div class="file-row" id="file-row-${i}">
        <span class="file-type-badge">${badge}</span>
        <span class="file-row-name" title="${f.name}">${f.name}</span>
        <span class="file-row-size">${fileSize(f.size)}</span>
        <span class="file-row-status queued" id="file-status-${i}">Queued</span>
        <button class="file-row-remove" onclick="removeFile(${i})">×</button>
      </div>`;
    }).join("")}`;
}

function setFileStatus(index, cls, text){
  const el = $(`#file-status-${index}`);
  if(!el) return;
  el.className = `file-row-status ${cls}`;
  el.textContent = text;
  // Hide remove button once processing starts
  const rm = $(`#file-row-${index} .file-row-remove`);
  if(rm) rm.style.visibility = "hidden";
}

function waitForPiiDecision(index){
  return new Promise(resolve => {
    const row = $(`#file-row-${index}`);
    const div = document.createElement("div");
    div.className = "pii-decision";
    div.innerHTML = `<span>PII detected — upload with redaction?</span>
      <button class="progress-btn done pii-yes">Yes, redact &amp; upload</button>
      <button class="progress-btn pii-no">Skip</button>`;
    row.appendChild(div);
    div.querySelector(".pii-yes").addEventListener("click", () => { div.remove(); resolve("upload"); });
    div.querySelector(".pii-no").addEventListener("click",  () => { div.remove(); resolve("skip"); });
  });
}

async function uploadOneFile(file, index, project, allowPii=false){
  setFileStatus(index, "uploading", "Uploading…");
  const form = new FormData();
  form.append("file", file);
  form.append("uploaded_by", state.employeeId || "anonymous");
  form.append("project", project);
  form.append("allow_pii", allowPii ? "true" : "false");
  try{
    const res = await fetch(`${API_BASE}/ingest`, {method:"POST", body:form});
    const data = await res.json();
    if(res.ok){
      if(data.status === "rejected_pii"){
        setFileStatus(index, "pii", "PII Detected");
        const decision = await waitForPiiDecision(index);
        if(decision === "upload"){
          return await uploadOneFile(file, index, project, true);
        }else{
          setFileStatus(index, "skipped", "Skipped");
          return "skipped";
        }
      }else if(data.status === "success"){
        setFileStatus(index, "success", data.pii_detected ? "Done (redacted)" : "Done");
        return "success";
      }else if(data.status === "duplicate"){
        setFileStatus(index, "duplicate", "Duplicate");
        return "duplicate";
      }else{
        setFileStatus(index, "error", "Error");
        return "error";
      }
    }else{
      setFileStatus(index, "error", data.detail || "Failed");
      return "error";
    }
  }catch(err){
    setFileStatus(index, "error", err.message);
    return "error";
  }
}

async function submitUpload(){
  if(selectedFiles.length === 0){ toast("Please select files.", "error"); return; }
  if(isUploading) return;
  isUploading = true;
  const btn = $("#upload-btn");
  btn.disabled = true;
  const project = $("#upload-project").value.trim();
  const counts = {success:0, duplicate:0, skipped:0, error:0};

  for(let i = 0; i < selectedFiles.length; i++){
    btn.textContent = `Uploading ${i+1} of ${selectedFiles.length}…`;
    const result = await uploadOneFile(selectedFiles[i], i, project);
    if(counts[result] !== undefined) counts[result]++;
  }

  isUploading = false;
  btn.textContent = "Upload All";
  btn.disabled = false;

  // Summary card
  const summary = $("#upload-summary");
  const total = selectedFiles.length;
  const hasError = counts.error > 0;
  summary.style.display = "block";
  summary.className = `result-card ${hasError ? "error" : counts.success > 0 ? "success" : "warning"}`;
  summary.innerHTML = `<strong>Upload Complete</strong> — ${total} file${total>1?"s":""} processed<br>
    <small>
      ${counts.success > 0 ? `${counts.success} uploaded &nbsp;` : ""}
      ${counts.duplicate > 0 ? `${counts.duplicate} duplicate &nbsp;` : ""}
      ${counts.skipped > 0 ? `${counts.skipped} skipped &nbsp;` : ""}
      ${counts.error > 0 ? `${counts.error} failed` : ""}
    </small>`;
}

// ── Profile ───────────────────────────────────────────────────────────────────

async function loadProfilePanel(){
  if(!state.employeeId) return;
  try{
    const profile = await apiFetch(`/profile/${state.employeeId}`);
    $("#pf-role").value = profile.role;
    $("#pf-experience").value = profile.experience_level;
    updateSidebarProfile(profile);
    const progress = await apiFetch(`/profile/${state.employeeId}/progress`);
    const list = $("#progress-list"); list.innerHTML = "";
    if(!progress.length){
      list.innerHTML = "<p style='color:var(--text-dim);font-size:.85rem'>No topics tracked yet. Ask the assistant for recommendations or a learning plan to get started.</p>";
    }else{
      progress.forEach(p => {
        const item = document.createElement("div");
        item.className = "progress-item";
        const sc = p.status.toLowerCase().replace(/ /g,"_");
        const actions = p.status !== "Completed"
          ? `<div class="progress-actions">
               ${p.status !== "In Progress" ? `<button class="progress-btn inprogress" data-topic="${p.topic}" data-status="In Progress">Start</button>` : ""}
               <button class="progress-btn done" data-topic="${p.topic}" data-status="Completed">Mark Done</button>
             </div>`
          : "";
        item.innerHTML = `<span class="progress-topic">${p.topic}</span>
          <div style="display:flex;align-items:center;gap:10px">
            <span class="status-badge ${sc}">${p.status}</span>
            ${actions}
          </div>`;
        list.appendChild(item);
      });

      // Attach click handlers for progress buttons
      $$(".progress-btn", list).forEach(btn => {
        btn.addEventListener("click", async () => {
          const topic = btn.dataset.topic;
          const status = btn.dataset.status;
          try{
            await apiFetch(`/profile/${state.employeeId}/progress`, {
              method: "POST",
              body: JSON.stringify({ employee_id: state.employeeId, topic, status })
            });
            toast(status === "Completed" ? `"${topic}" marked as done!` : `Started "${topic}"`, "success");
            loadProfilePanel(); // refresh the list
          }catch(err){ toast(err.message, "error"); }
        });
      });
    }
  }catch(err){ toast(err.message, "error"); }
}

async function saveProfile(){
  try{
    await apiFetch(`/profile/${state.employeeId}`, {
      method: "PATCH", body: JSON.stringify({
        role: $("#pf-role").value,
        experience_level: $("#pf-experience").value
      })
    });
    toast("Profile updated.", "success");
    updateSidebarProfile({name: state.name, role: $("#pf-role").value});
  }catch(err){ toast(err.message, "error"); }
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  setupDropZone();

  // Nav
  $$(".nav-item[data-panel]").forEach(btn => {
    btn.addEventListener("click", () => navigateTo(btn.dataset.panel));
  });
  $("#nav-logout").addEventListener("click", logout);

  // Chat input
  const input = $("#chat-input");
  input.addEventListener("keydown", e => {
    if(e.key === "Enter" && !e.shiftKey){ e.preventDefault(); sendMessage(); }
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
  });
  $("#send-btn").addEventListener("click", sendMessage);

  // Auth
  $("#login-password").addEventListener("keydown", e => { if(e.key==="Enter") login(); });
  $("#login-btn").addEventListener("click", login);
  $("#setup-submit-btn").addEventListener("click", submitProfileSetup);

  // Profile
  $("#upload-btn").addEventListener("click", submitUpload);
  $("#save-profile-btn").addEventListener("click", saveProfile);

  // Project picker buttons
  $$(".project-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      $$(".project-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.selectedProject = btn.dataset.project;
      updateSidebarProject();
      toast(`Project set to ${btn.dataset.project}`, "success");
    });
  });

  // Restore session
  if(loadSession()){
    showAuthNav(true);
    updateSidebarProject();
    if(!state.profileComplete){
      // Returning user who never finished profile — back to setup panel
      showPanel("setup");
    }else{
      apiFetch(`/profile/${state.employeeId}`)
        .then(p => updateSidebarProfile(p))
        .catch(() => updateSidebarProfile({name: state.name}));
      if(state.sessionId) $("#session-badge").textContent = `Session: ${state.sessionId.slice(0,8)}`;
      navigateTo("chat");
      toast(`Welcome back, ${state.name}!`, "success");
    }
  }else{
    showAuthNav(false);
    showPanel("login");
  }
});
