// ── 초기화 ───────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  checkAuth();
  
  // 관리자만 사용자 관리 메뉴 표시
  if (getRole() === "admin") {
    document.getElementById("nav-users").style.display = "block";
    document.getElementById("settings-section").style.display = "block";
    document.getElementById("report-generate-btn").style.display = "block";
  }

  fetchEvents();
  fetchReports();
  fetchSettings();
  setInterval(fetchEvents, 3000);
});

// ── 로그아웃 ─────────────────────────────────
function logout() {
  clearToken();
  window.location.href = "index.html";
}

// ── 이벤트 목록 ──────────────────────────────
async function fetchEvents() {
  try {
    const events = await apiGetEvents();

    // 서버 연결 상태
    document.getElementById("status").textContent      = "● 서버 연결됨";
    document.getElementById("status").style.background = "#27ae60";

    // 요약 카드
    const fallCount = events.filter(e => e.type.includes("낙상")).length;
    const sosCount  = events.filter(e =>
      e.type.includes("SOS") || e.type.includes("음성")
    ).length;

    document.getElementById("fall-count").textContent  = fallCount;
    document.getElementById("sos-count").textContent   = sosCount;
    document.getElementById("total-count").textContent = events.length;

    // 이벤트 목록
    const list = document.getElementById("event-list");
    if (events.length === 0) {
      list.innerHTML = '<div class="empty">이벤트가 없습니다</div>';
      return;
    }

    list.innerHTML = events.map(e => `
      <div class="list-item">
        <span class="badge ${getBadgeClass(e.type)}">${e.type}</span>
        <div style="flex:1">
          <div style="font-size:14px;font-weight:600">${e.room}</div>
          <div style="font-size:12px;color:#888;margin-top:2px">${e.message}</div>
        </div>
        <div style="font-size:12px;color:#aaa">${e.timestamp}</div>
      </div>
    `).join("");

  } catch (err) {
    document.getElementById("status").textContent      = "● 서버 연결 끊김";
    document.getElementById("status").style.background = "#e74c3c";
  }
}

function getBadgeClass(type) {
  if (type.includes("낙상")) return "fall";
  if (type.includes("SOS") || type.includes("음성")) return "sos";
  return "default";
}

// ── 리포트 ───────────────────────────────────
async function fetchReports() {
  try {
    const reports = await apiGetReports();
    const list    = document.getElementById("report-list");

    if (reports.length === 0) {
      list.innerHTML = '<div class="empty">리포트가 없습니다</div>';
      return;
    }

    list.innerHTML = reports.map(r => `
      <div class="list-item">
        <div style="flex:1">
          <div style="font-size:14px;font-weight:600">${r.filename}</div>
          <div style="font-size:12px;color:#888;margin-top:2px">${r.month}</div>
        </div>
        <a class="btn btn-primary"
           href="${SERVER}/reports/download/${r.month}/${r.filename}"
           target="_blank">
          다운로드
        </a>
      </div>
    `).join("");

  } catch (err) {
    console.error("리포트 불러오기 실패:", err);
  }
}

async function generateReport() {
  try {
    const data = await apiGenerateReport();
    alert(`✅ 리포트 생성 완료!\n${data.filename}`);
    fetchReports();
  } catch (err) {
    alert("❌ 리포트 생성 실패");
  }
}

// ── 설정 ─────────────────────────────────────
async function fetchSettings() {
  try {
    const settings = await apiGetSettings();

    document.querySelectorAll("input[name='interval']").forEach(el => {
      el.checked = el.value === settings.report_interval;
    });

    document.getElementById("report-day").value  = settings.report_day;
    document.getElementById("report-time").value = settings.report_time;

    toggleDayRow(settings.report_interval);

  } catch (err) {
    console.error("설정 불러오기 실패:", err);
  }
}

async function saveSettings() {
  const interval = document.querySelector("input[name='interval']:checked").value;
  const day      = document.getElementById("report-day").value;
  const time     = document.getElementById("report-time").value;

  try {
    await apiSaveSettings({
      report_interval: interval,
      report_time:     time,
      report_day:      day,
    });

    const msg = document.getElementById("save-msg");
    msg.classList.add("show");
    setTimeout(() => msg.classList.remove("show"), 2000);

  } catch (err) {
    alert("❌ 저장 실패");
  }
}

function toggleDayRow(interval) {
  document.getElementById("day-row").style.display =
    interval === "weekly" ? "flex" : "none";
}

document.querySelectorAll("input[name='interval']")?.forEach(el => {
  el.addEventListener("change", () => toggleDayRow(el.value));
});