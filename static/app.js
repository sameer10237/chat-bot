const form = document.querySelector("#chat-form");
const input = document.querySelector("#message");
const conversation = document.querySelector("#conversation");
const errorMessage = document.querySelector("#error");
const sendButton = document.querySelector("#send");
const history = [];

function addMessage(role, content, sources = []) {
  conversation.querySelector(".welcome")?.remove();

  const article = document.createElement("article");
  article.className = `message message-${role}`;
  const label = document.createElement("p");
  label.className = "message-label";
  label.textContent = role === "user" ? "You" : "Assistant";
  const body = document.createElement("p");
  body.className = "message-content";
  body.textContent = content;
  article.append(label, body);

  if (sources.length > 0) {
    const list = document.createElement("ul");
    list.className = "sources";
    for (const source of sources) {
      const item = document.createElement("li");
      const title = source.title || source.id;
      if (source.url) {
        try {
          const url = new URL(source.url);
          if (url.protocol === "https:" || url.protocol === "http:") {
            const link = document.createElement("a");
            link.href = url.href;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = title;
            item.append(link);
          } else {
            item.textContent = title;
          }
        } catch {
          item.textContent = title;
        }
      } else {
        item.textContent = title;
      }
      list.append(item);
    }
    article.append(list);
  }

  conversation.append(article);
  conversation.scrollTo({
    top: conversation.scrollHeight,
    behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? "auto"
      : "smooth",
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) {
    input.focus();
    return;
  }

  errorMessage.hidden = true;
  addMessage("user", message);
  input.value = "";
  input.disabled = true;
  sendButton.disabled = true;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error?.message || "The request could not be completed.");
    }
    if (typeof result.reply !== "string") {
      throw new Error("The server returned an invalid response.");
    }

    addMessage("assistant", result.reply, result.sources || []);
    history.push(
      { role: "user", content: message },
      { role: "assistant", content: result.reply },
    );
  } catch (error) {
    errorMessage.textContent = error instanceof Error
      ? error.message
      : "The request could not be completed.";
    errorMessage.hidden = false;
  } finally {
    input.disabled = false;
    sendButton.disabled = false;
    input.focus();
  }
});
