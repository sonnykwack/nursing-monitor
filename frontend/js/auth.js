async function login() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value.trim();
  const errorEl  = document.getElementById("login-error");

  if (!username || !password) {
    errorEl.textContent = "아이디와 비밀번호를 입력해주세요";
    return;
  }

  try {
    const data = await apiLogin(username, password);
    saveToken(data.access_token, data.role);

    // 역할에 따라 다른 페이지로 이동
    if (data.role === "admin") {
      window.location.href = "dashboard.html";
    } else {
      window.location.href = "dashboard.html";
    }

  } catch (err) {
    errorEl.textContent = err.message;
  }
}

// 엔터 키로 로그인
document.addEventListener("DOMContentLoaded", () => {
  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter") login();
  });
});