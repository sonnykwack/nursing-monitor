const SERVER = "http://127.0.0.1:8000";

// ── 토큰 관리 ────────────────────────────────
function getToken() {
  return localStorage.getItem("token");
}

function getRole() {
  return localStorage.getItem("role");
}

function saveToken(token, role) {
  localStorage.setItem("token", token);
  localStorage.setItem("role", role);
}

function clearToken() {
  localStorage.removeItem("token");
  localStorage.removeItem("role");
}

// ── 인증 헤더 ────────────────────────────────
function authHeaders() {
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${getToken()}`
  };
}

// ── 로그인 ───────────────────────────────────
async function apiLogin(username, password) {
  const res = await fetch(`${SERVER}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
  });
  if (!res.ok) throw new Error("아이디 또는 비밀번호가 틀렸어요");
  return res.json();
}

// ── 이벤트 ───────────────────────────────────
async function apiGetEvents() {
  const res = await fetch(`${SERVER}/events`, { headers: authHeaders() });
  if (res.status === 401) { redirectLogin(); return []; }
  return res.json();
}

// ── 리포트 ───────────────────────────────────
async function apiGetReports() {
  const res = await fetch(`${SERVER}/reports`, { headers: authHeaders() });
  if (res.status === 401) { redirectLogin(); return []; }
  return res.json();
}

async function apiGenerateReport() {
  const res = await fetch(`${SERVER}/reports/generate`, {
    method: "POST",
    headers: authHeaders()
  });
  if (res.status === 401) { redirectLogin(); return null; }
  return res.json();
}

// ── 설정 ─────────────────────────────────────
async function apiGetSettings() {
  const res = await fetch(`${SERVER}/settings`, { headers: authHeaders() });
  if (res.status === 401) { redirectLogin(); return null; }
  return res.json();
}

async function apiSaveSettings(data) {
  const res = await fetch(`${SERVER}/settings`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(data)
  });
  if (res.status === 401) { redirectLogin(); return null; }
  return res.json();
}

// ── 사용자 관리 ──────────────────────────────
async function apiGetUsers() {
  const res = await fetch(`${SERVER}/users`, { headers: authHeaders() });
  if (res.status === 401) { redirectLogin(); return []; }
  return res.json();
}

async function apiCreateUser(data) {
  const res = await fetch(`${SERVER}/users`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(data)
  });
  if (res.status === 401) { redirectLogin(); return null; }
  return res.json();
}

async function apiDeleteUser(id) {
  const res = await fetch(`${SERVER}/users/${id}`, {
    method: "DELETE",
    headers: authHeaders()
  });
  if (res.status === 401) { redirectLogin(); return null; }
  return res.json();
}

// ── 로그인 페이지로 이동 ─────────────────────
function redirectLogin() {
  clearToken();
  window.location.href = "index.html";
}

// ── 로그인 여부 확인 ─────────────────────────
function checkAuth() {
  if (!getToken()) redirectLogin();
}

// ── 관리자 여부 확인 ─────────────────────────
function checkAdmin() {
  if (getRole() !== "admin") {
    alert("관리자만 접근 가능해요!");
    window.location.href = "dashboard.html";
  }
}