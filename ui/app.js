const chatEl = document.getElementById("chat");
const form = document.getElementById("composer");
const messageInput = document.getElementById("message");
const sendBtn = document.getElementById("send-btn");

const welcome = document.createElement("div");
welcome.className = "bubble assistant";
welcome.innerHTML =
  "<p class=\"answer\">Welcome. Ask factual questions about expense ratio, exit load, minimum SIP, benchmark, tax, or fund managers for the five supported HDFC schemes on Groww.</p>";
chatEl.appendChild(welcome);

function appendBubble(role, html, extraClass = "") {
  const div = document.createElement("div");
  div.className = `bubble ${role} ${extraClass}`.trim();
  div.innerHTML = html;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
  return div;
}

function formatResponse(data) {
  const linkLabel = data.is_refusal ? "Learn more" : "Source";
  const citation = data.citation_url
    ? `<a href="${escapeHtml(data.citation_url)}" target="_blank" rel="noopener noreferrer">${linkLabel}</a> · `
    : "";
  const footer = `Last updated from sources: ${escapeHtml(data.last_updated)}`;
  return `
    <p class="answer">${formatAnswerText(data.answer)}</p>
    <p class="meta">${citation}${footer}</p>
  `;
}

function formatAnswerText(text) {
  return escapeHtml(text).replace(/\n/g, "<br>");
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function sendMessage(text) {
  const trimmed = text.trim();
  if (!trimmed) return;

  appendBubble("user", `<p class="answer">${escapeHtml(trimmed)}</p>`);
  messageInput.value = "";
  sendBtn.disabled = true;

  const loading = appendBubble("assistant", '<p class="loading">Thinking…</p>');

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: trimmed }),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const detail = data.detail || res.statusText || "Request failed";
      loading.innerHTML = `<p class="error-text">${escapeHtml(String(detail))}</p>`;
      loading.classList.add("refusal");
      return;
    }

    loading.className = `bubble assistant ${data.is_refusal ? "refusal" : ""}`.trim();
    loading.innerHTML = formatResponse(data);
  } catch (err) {
    loading.innerHTML = `<p class="error-text">Could not reach the server. Is the API running on this host?</p>`;
  } finally {
    sendBtn.disabled = false;
    messageInput.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(messageInput.value);
});

document.querySelectorAll(".example-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const msg = btn.getAttribute("data-message");
    messageInput.value = msg;
    sendMessage(msg);
  });
});
