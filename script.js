/**
 * script.js
 * Frontend JavaScript for Nexus AI Assistant. Handles:
 *  - Google Sign-In token submission
 *  - Chat interactions (sending user messages, receiving responses)
 *  - Monitoring events via SSE (Server-Sent Events)
 *  - Voice input/output triggers
 *  - Session title handling
 *  - Plugin listing
 *  - Celery long task demo
 */

/**
 * Handle Google Credential Response
 * This function is called automatically by Google's "g_id_onload" callback
 * once the user logs in via the Google One Tap prompt or button.
 */
function handleCredentialResponse(response) {
  const formData = new FormData();
  formData.append('id_token', response.credential);

  fetch('/auth/google/callback', {
    method: 'POST',
    body: formData
  })
    .then(res => res.json())
    .then(data => {
      if (data.status === "success") {
        window.location.reload();
      } else {
        alert("Google Login Failed: " + data.message);
      }
    })
    .catch(err => {
      console.error("Error verifying Google ID token:", err);
    });
}

/***************************************************************
 * Chat Interactions
 ***************************************************************/

/**
 * Initialize chat form listener. 
 * When the user submits the chat form, send their message to the server.
 */
function initChatForm() {
  const chatForm = document.getElementById('chat-form');
  if (!chatForm) return; // Might not exist if user is not logged in

  chatForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const userInput = document.getElementById('user-input');
    if (!userInput.value.trim()) {
      return;
    }
    // Display user's message in the chat box
    addChatMessage('user', userInput.value.trim());

    // Send the request to /api/v1/process
    const payload = {
      request: userInput.value.trim(),
      params: {}  // Add any additional params if needed
    };

    fetch('/api/v1/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(res => res.json())
      .then(data => {
        if (data.status === "success") {
          // Display AI's response in the chat box
          addChatMessage('assistant', data.response);
        } else {
          addChatMessage('assistant', "Error: " + (data.message || "Unknown error"));
        }
      })
      .catch(err => {
        addChatMessage('assistant', "Error sending message: " + err.message);
      });

    userInput.value = "";
  });
}

/**
 * Add a message to the chat box.
 * @param {string} sender - "user" or "assistant"
 * @param {string} text   - Message content
 */
function addChatMessage(sender, text) {
  const chatBox = document.getElementById('chat-box');
  if (!chatBox) return;

  const msgDiv = document.createElement('div');
  msgDiv.classList.add(sender === 'user' ? 'user-message' : 'assistant-message');
  msgDiv.textContent = text;
  chatBox.appendChild(msgDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

/***************************************************************
 * SSE (Monitor / Event Streaming)
 ***************************************************************/

/**
 * Initialize the event source for the /api/v1/monitor endpoint.
 * Streams real-time events from the server into the #monitor-box.
 */
function initMonitorStream() {
  const monitorBox = document.getElementById('monitor-box');
  if (!monitorBox) return; // Might not exist if user is not logged in

  const source = new EventSource('/api/v1/monitor');
  source.onmessage = function (event) {
    const data = event.data;
    const lineDiv = document.createElement('div');
    lineDiv.classList.add('monitor-event');
    lineDiv.textContent = data;
    monitorBox.appendChild(lineDiv);

    // Force fade-in effect
    setTimeout(() => {
      lineDiv.classList.add('fade-in');
    }, 50);

    monitorBox.scrollTop = monitorBox.scrollHeight;
  };
  source.onerror = function (err) {
    console.error("Monitor stream error:", err);
    // Optionally handle errors or reconnect logic
  };
}

/***************************************************************
 * Voice Input / Output
 ***************************************************************/

/**
 * Listen function is called from the 'Listen' button in index.html.
 * It triggers the server's voice recognition route.
 */
function listen() {
  fetch('/api/v1/voice/listen', {
    method: 'POST'
  })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        const userInput = document.getElementById('user-input');
        userInput.value = data.text;
        document.getElementById('chat-form').dispatchEvent(new Event('submit'));
      } else {
        alert(data.message);
      }
    });
}

/**
 * Speak function (optional). 
 * Send text to server for TTS output.
 */
function speak(text) {
  fetch('/api/v1/voice/speak', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: text })
  })
    .then(response => response.json())
    .then(data => {
      if (data.status !== 'success') {
        alert("Error speaking text: " + data.message);
      }
    });
}

/***************************************************************
 * Session Title Management
 ***************************************************************/

/**
 * Set session title using the /api/v1/set_session_title endpoint.
 */
function setSessionTitle() {
  const titleInput = document.getElementById('session-title-input');
  if (!titleInput) return;
  const newTitle = titleInput.value.trim();
  if (!newTitle) {
    alert("Please enter a valid title.");
    return;
  }

  fetch('/api/v1/set_session_title', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: newTitle })
  })
    .then(res => res.json())
    .then(data => {
      if (data.status === "success") {
        document.getElementById('current-title').textContent = newTitle;
        alert(data.message);
      } else {
        alert("Error: " + data.message);
      }
    });
}

/**
 * Review sessions by fetching session titles from /api/v1/session_titles
 * and populating a <select> with them.
 */
function reviewSessions() {
  const sessionSelect = document.getElementById('session-title-select');
  if (!sessionSelect) return;

  fetch('/api/v1/session_titles')
    .then(res => res.json())
    .then(data => {
      if (data.status === "success") {
        sessionSelect.innerHTML = "<option value=''>Select a session to review</option>";
        data.titles.forEach(title => {
          const option = document.createElement('option');
          option.value = title;
          option.textContent = title;
          sessionSelect.appendChild(option);
        });
      } else {
        alert("Error fetching sessions: " + data.message);
      }
    })
    .catch(err => {
      alert("Error: " + err.message);
    });
}

/***************************************************************
 * Plugin Handling
 ***************************************************************/

/**
 * Fetch and display plugins from /api/v1/plugins.
 */
function fetchPlugins() {
  const pluginList = document.getElementById('plugin-list');
  if (!pluginList) return;

  fetch('/api/v1/plugins')
    .then(res => res.json())
    .then(data => {
      if (data.status === "success") {
        pluginList.innerHTML = "";
        data.plugins.forEach(plugin => {
          const li = document.createElement('li');
          li.classList.add('list-group-item');
          li.textContent = `${plugin.name} - ${plugin.description}`;
          pluginList.appendChild(li);
        });
      } else {
        alert("Error fetching plugins: " + data.message);
      }
    })
    .catch(err => {
      console.error("Error fetching plugins:", err);
    });
}

/***************************************************************
 * Celery Long Task Demo
 ***************************************************************/

/**
 * Trigger a Celery long task for demonstration.
 */
function runCeleryTask() {
  fetch('/api/v1/task', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: 'Celery Test Data' })
  })
    .then(response => response.json())
    .then(data => {
      document.getElementById('task-status').textContent = `Task ID: ${data.task_id}`;
      checkTaskStatus(data.task_id);
    });
}

/**
 * Poll task status periodically until it's finished.
 */
function checkTaskStatus(taskId) {
  const intervalId = setInterval(() => {
    fetch(`/api/v1/task_status/${taskId}`)
      .then(response => response.json())
      .then(data => {
        document.getElementById('task-status').textContent =
          `Task Status: ${data.status}, Result: ${data.result || 'N/A'}`;
        if (data.status === 'SUCCESS' || data.status === 'FAILURE') {
          clearInterval(intervalId);
        }
      })
      .catch(err => {
        console.error("Error checking task status:", err);
      });
  }, 3000);
}

/***************************************************************
 * Initialization on Page Load
 ***************************************************************/
document.addEventListener('DOMContentLoaded', () => {
  initChatForm();
  initMonitorStream();
  fetchPlugins();
  // If needed, you can also auto-call reviewSessions() here
});
