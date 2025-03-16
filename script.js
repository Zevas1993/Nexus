/**
 * script.js
 * Main JavaScript file for Nexus AI Assistant
 */

// Global variables
let eventSource = null;
let currentSessionId = null;

/**
 * Document ready function
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initChatForm();
    initMonitorStream();
    initSessionManagement();
    
    // Check if URL contains a prompt parameter
    const urlParams = new URLSearchParams(window.location.search);
    const promptParam = urlParams.get('prompt');
    if (promptParam) {
        // Set the prompt in the input field and submit
        const userInput = document.getElementById('user-input');
        if (userInput) {
            userInput.value = promptParam;
            // Submit the form after a short delay to ensure everything is loaded
            setTimeout(() => {
                document.getElementById('chat-form')?.dispatchEvent(new Event('submit'));
            }, 500);
        }
    }
});

/**
 * Handle Google Credential Response
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
        alert("Login error: " + err.message);
    });
}

/**
 * Initialize chat form
 */
function initChatForm() {
    const chatForm = document.getElementById('chat-form');
    if (!chatForm) return;

    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const userInput = document.getElementById('user-input');
        const message = userInput.value.trim();
        
        if (!message) return;
        
        // Add user message to chat
        addChatMessage('user', message);
        
        // Clear input
        userInput.value = '';
        
        // Get current session ID
        const sessionId = currentSessionId || (document.querySelector('[data-session-id]')?.dataset.sessionId);
        
        // Send request to API
        fetch('/api/v1/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                request: message,
                params: {
                    session_id: sessionId
                }
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Add assistant response to chat
                addChatMessage('assistant', data.response);
                
                // Speak response if speech synthesis is enabled
                if (localStorage.getItem('enableSpeech') === 'true') {
                    speak(data.response);
                }
            } else {
                // Add error message
                addChatMessage('assistant', 'Error: ' + (data.message || 'Unknown error'));
            }
        })
        .catch(err => {
            console.error('Error processing request:', err);
            addChatMessage('assistant', 'Error: Could not process your request.');
        });
    });
}

/**
 * Add message to chat
 */
function addChatMessage(role, content) {
    const chatBox = document.getElementById('chat-box');
    if (!chatBox) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = role === 'user' ? 'message user-message fade-in-animation' : 'message assistant-message fade-in-animation';
    messageDiv.textContent = content;
    chatBox.appendChild(messageDiv);
    
    // Scroll to bottom
    chatBox.scrollTop = chatBox.scrollHeight;
}

/**
 * Initialize monitor stream
 */
function initMonitorStream() {
    const monitorBox = document.getElementById('monitor-box');
    if (!monitorBox) return;

    // Close existing event source if any
    if (eventSource) {
        eventSource.close();
    }

    // Create new event source
    eventSource = new EventSource('/api/v1/monitor');
    
    eventSource.onmessage = function(event) {
        const data = event.data;
        const lineDiv = document.createElement('div');
        lineDiv.classList.add('monitor-event');
        lineDiv.textContent = data;
        monitorBox.appendChild(lineDiv);

        // Force fade-in effect
        setTimeout(() => {
            lineDiv.classList.add('fade-in');
        }, 50);

        // Scroll to bottom
        monitorBox.scrollTop = monitorBox.scrollHeight;
        
        // Limit number of events shown
        while (monitorBox.children.length > 100) {
            monitorBox.removeChild(monitorBox.firstChild);
        }
    };
    
    eventSource.onerror = function(err) {
        console.error("Monitor stream error:", err);
        // Try to reconnect after a delay
        setTimeout(() => {
            initMonitorStream();
        }, 5000);
    };
}

/**
 * Initialize session management
 */
function initSessionManagement() {
    // Set current session ID if available
    const sessionElement = document.querySelector('[data-session-id]');
    if (sessionElement) {
        currentSessionId = sessionElement.dataset.sessionId;
    }
    
    // Session title input
    const sessionTitleInput = document.getElementById('session-title-input');
    const currentTitleSpan = document.getElementById('current-title');
    
    if (sessionTitleInput && currentTitleSpan) {
        // Set initial value from current title
        sessionTitleInput.value = currentTitleSpan.textContent;
        
        // Add event listener for Enter key
        sessionTitleInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                setSessionTitle();
            }
        });
    }
}

/**
 * Set session title
 */
function setSessionTitle() {
    const titleInput = document.getElementById('session-title-input');
    const currentTitle = document.getElementById('current-title');
    
    if (!titleInput || !currentTitle) return;
    
    const newTitle = titleInput.value.trim();
    if (!newTitle) {
        alert("Please enter a valid title.");
        return;
    }
    
    // Get current session ID
    const sessionId = currentSessionId || (document.querySelector('[data-session-id]')?.dataset.sessionId);
    
    if (sessionId) {
        // Update existing session
        fetch(`/api/v1/session/${sessionId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: newTitle
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                currentTitle.textContent = newTitle;
                alert(`Session title updated to: ${newTitle}`);
            } else {
                alert('Error updating session title: ' + data.message);
            }
        })
        .catch(err => {
            console.error('Error updating session title:', err);
            alert('Error updating session title. Please try again.');
        });
    } else {
        // Create new session
        fetch('/api/v1/session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: newTitle
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                currentSessionId = data.session.id;
                currentTitle.textContent = newTitle;
                alert(`New session created: ${newTitle}`);
            } else {
                alert('Error creating session: ' + data.message);
            }
        })
        .catch(err => {
            console.error('Error creating session:', err);
            alert('Error creating session. Please try again.');
        });
    }
}

/**
 * Voice input function
 */
function listen() {
    // Show listening indicator
    const userInput = document.getElementById('user-input');
    if (userInput) {
        const originalPlaceholder = userInput.placeholder;
        userInput.placeholder = "Listening...";
        
        fetch('/api/v1/voice/listen', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            // Restore original placeholder
            userInput.placeholder = originalPlaceholder;
            
            if (data.status === 'success') {
                userInput.value = data.text;
                document.getElementById('chat-form')?.dispatchEvent(new Event('submit'));
            } else {
                alert('Error: ' + (data.message || 'Could not understand audio'));
            }
        })
        .catch(err => {
            // Restore original placeholder
            userInput.placeholder = originalPlaceholder;
            console.error('Error with voice recognition:', err);
            alert('Error with voice recognition. Please try again.');
        });
    }
}

/**
 * Voice output function
 */
function speak(text) {
    fetch('/api/v1/voice/speak', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            text: text
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status !== 'success') {
            console.error('Error speaking text:', data.message);
        }
    })
    .catch(err => {
        console.error('Error with speech synthesis:', err);
    });
}

/**
 * Toggle dark mode
 */
function toggleDarkMode() {
    const body = document.body;
    body.classList.toggle('dark-mode');
    
    // Save preference
    const isDarkMode = body.classList.contains('dark-mode');
    localStorage.setItem('darkMode', isDarkMode);
    
    return isDarkMode;
}

/**
 * Check if dark mode is enabled
 */
function isDarkModeEnabled() {
    // Check localStorage first
    const storedPreference = localStorage.getItem('darkMode');
    if (storedPreference !== null) {
        return storedPreference === 'true';
    }
    
    // Check system preference
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
}

/**
 * Apply dark mode if enabled
 */
function applyDarkModeIfEnabled() {
    if (isDarkModeEnabled()) {
        document.body.classList.add('dark-mode');
    }
}

// Apply dark mode on page load
document.addEventListener('DOMContentLoaded', applyDarkModeIfEnabled);

/**
 * Create a new Celery task
 */
function runCeleryTask() {
    fetch('/api/v1/task', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            data: 'Celery Test Data'
        })
    })
    .then(response => response.json())
    .then(data => {
        const taskStatus = document.getElementById('task-status');
        if (taskStatus) {
            taskStatus.textContent = `Task ID: ${data.task_id}`;
            checkTaskStatus(data.task_id);
        }
    })
    .catch(err => {
        console.error('Error creating task:', err);
        alert('Error creating task: ' + err.message);
    });
}

/**
 * Check Celery task status
 */
function checkTaskStatus(taskId) {
    const taskStatus = document.getElementById('task-status');
    if (!taskStatus) return;
    
    const intervalId = setInterval(() => {
        fetch(`/api/v1/task_status/${taskId}`)
        .then(response => response.json())
        .then(data => {
            taskStatus.textContent = `Task Status: ${data.status}, Result: ${data.result || 'N/A'}`;
            
            if (data.status === 'SUCCESS' || data.status === 'FAILURE') {
                clearInterval(intervalId);
            }
        })
        .catch(err => {
            console.error('Error checking task status:', err);
            taskStatus.textContent = `Error checking task status: ${err.message}`;
            clearInterval(intervalId);
        });
    }, 3000);
}
