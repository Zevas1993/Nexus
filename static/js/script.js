document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatBox = document.getElementById('chat-box');
    const monitorDiv = document.getElementById('monitor-box');

    // Set up SSE for monitoring
    if (monitorDiv) {
        const eventSource = new EventSource('/api/v1/monitor');
        eventSource.onmessage = function(event) {
            const eventText = event.data;
            const eventElement = document.createElement('div');
            eventElement.className = 'monitor-event';
            eventElement.textContent = eventText;
            monitorDiv.appendChild(eventElement);
            monitorDiv.scrollTop = monitorDiv.scrollHeight;
            eventElement.classList.add('fade-in');
        };
        eventSource.onerror = function() {
            console.error('Monitor stream error');
            eventSource.close();
        };
    }

    // Set up chat form
    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = userInput.value.trim();
            if (!message) return;

            // Add user message to chat
            const userDiv = document.createElement('div');
            userDiv.className = 'user-message';
            userDiv.textContent = message;
            chatBox.appendChild(userDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
            userInput.value = '';

            // Show thinking indicator
            const thinkingDiv = document.createElement('div');
            thinkingDiv.className = 'assistant-message thinking';
            thinkingDiv.textContent = 'Thinking...';
            chatBox.appendChild(thinkingDiv);
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                // Process request
                const response = await fetch('/api/v1/process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ request: message })
                });
                const result = await response.json();

                // Remove thinking indicator
                chatBox.removeChild(thinkingDiv);

                // Add assistant response
                const assistantDiv = document.createElement('div');
                assistantDiv.className = 'assistant-message';
                
                if (result.status === 'success') {
                    if (result.results) {
                        // Process results from various services
                        let responseText = '';
                        
                        Object.entries(result.results).forEach(([service, data]) => {
                            // Service-specific formatting
                            if (service === 'language_model' || service === 'general_query') {
                                responseText += data.text || '';
                            } else if (service === 'translation') {
                                responseText += data.translation || '';
                            } else if (service === 'code') {
                                responseText += data.code || '';
                            } else if (typeof data === 'object') {
                                responseText += JSON.stringify(data, null, 2);
                            } else {
                                responseText += data.toString();
                            }
                            responseText += '\n\n';
                        });
                        
                        assistantDiv.textContent = responseText.trim();
                    } else {
                        // Generic success response
                        assistantDiv.textContent = result.text || 'Request processed successfully.';
                    }
                } else {
                    // Error response
                    assistantDiv.textContent = `Error: ${result.message || 'Unknown error'}`;
                    assistantDiv.classList.add('error');
                }
                
                chatBox.appendChild(assistantDiv);
                chatBox.scrollTop = chatBox.scrollHeight;
            } catch (error) {
                console.error('Request error:', error);
                // Remove thinking indicator
                chatBox.removeChild(thinkingDiv);
                
                // Add error message
                const errorDiv = document.createElement('div');
                errorDiv.className = 'assistant-message error';
                errorDiv.textContent = 'Error: Unable to process request. Please try again.';
                chatBox.appendChild(errorDiv);
            }
        });
    }
});
