document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded');
    
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const cleanupBtn = document.getElementById('cleanupBtn');
    const scrapeBtn = document.getElementById('scrapeBtn');
    const urlModal = document.getElementById('urlModal');
    const urlForm = document.getElementById('urlForm');
    const closeModalBtn = document.getElementById('close-modal');

    console.log('Elements found:', {
        chatBox: !!chatBox,
        userInput: !!userInput,
        sendButton: !!sendButton,
        cleanupBtn: !!cleanupBtn,
        scrapeBtn: !!scrapeBtn,
        urlModal: !!urlModal,
        urlForm: !!urlForm,
        closeModalBtn: !!closeModalBtn
    });

    // Add event listeners
    sendButton.addEventListener('click', function() {
        console.log('Send button clicked');
        sendMessage();
    });
    
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            console.log('Enter key pressed');
            sendMessage();
        }
    });

    cleanupBtn.addEventListener('click', function() {
        console.log('Cleanup button clicked');
        cleanupData();
    });
    
    scrapeBtn.addEventListener('click', function() {
        console.log('Scrape button clicked');
        showUrlModal();
    });
    
    urlForm.addEventListener('submit', function(e) {
        console.log('URL form submitted');
        handleUrlSubmit(e);
    });
    
    closeModalBtn.addEventListener('click', function() {
        console.log('Close modal clicked');
        hideModal();
    });

    function showUrlModal() {
        urlModal.style.display = 'block';
    }

    function hideModal() {
        urlModal.style.display = 'none';
        urlForm.reset();
    }

    // Close modal when clicking outside
    window.addEventListener('click', function(e) {
        if (e.target === urlModal) {
            hideModal();
        }
    });

    async function handleUrlSubmit(e) {
        e.preventDefault();
        
        const url = document.getElementById('urlInput').value;
        const name = document.getElementById('nameInput').value;

        hideModal();
        scrapeBtn.disabled = true;
        scrapeBtn.textContent = 'Scraping...';
        
        try {
            const response = await fetch('/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url,
                    name
                }),
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                addMessageToChat(`Data scraping completed successfully. ${data.message}`, 'bot');
            } else {
                addMessageToChat(`Scraping failed: ${data.message}`, 'bot');
            }
        } catch (error) {
            console.error('Error:', error);
            addMessageToChat('Failed to scrape data. Please try again.', 'bot');
        } finally {
            scrapeBtn.disabled = false;
            scrapeBtn.textContent = 'Scrape New URL';
        }
    }

    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        console.log('Sending message:', message);

        // Add user message to chat
        addMessageToChat(message, 'user');
        userInput.value = '';

        try {
            console.log('Making fetch request to /chat');
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ message }),
            });

            console.log('Response received:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Response data:', data);
            
            if (data.error) {
                addMessageToChat('Sorry, I encountered an error. Please try again.', 'bot');
                return;
            }

            // Store the response for chunk information
            window.lastResponse = data;
            
            // Format the response by splitting into lines and removing empty ones
            const formattedResponse = data.response
                .split('\n')
                .map(line => line.trim())
                .filter(line => line.length > 0)
                .join('\n\n');
            
            addMessageToChat(formattedResponse, 'bot');
        } catch (error) {
            console.error('Error in sendMessage:', error);
            addMessageToChat('Sorry, I encountered an error. Please try again.', 'bot');
        }
    }

    async function cleanupData() {
        cleanupBtn.disabled = true;
        cleanupBtn.textContent = 'Cleaning...';
        
        try {
            const response = await fetch('/cleanup', {
                method: 'POST',
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                addMessageToChat('Data cleanup completed successfully.', 'bot');
            } else {
                addMessageToChat(`Cleanup failed: ${data.message}`, 'bot');
            }
        } catch (error) {
            console.error('Error:', error);
            addMessageToChat('Failed to clean up data. Please try again.', 'bot');
        } finally {
            cleanupBtn.disabled = false;
            cleanupBtn.textContent = 'Clean Up Data';
        }
    }

    function addMessageToChat(message, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = message.replace(/\n/g, '<br>');
        messageDiv.appendChild(contentDiv);
        
        // Add chunk information if available
        if (sender === 'bot' && window.lastResponse && window.lastResponse.chunks && window.lastResponse.chunks.length > 0) {
            const chunksDiv = document.createElement('div');
            chunksDiv.className = 'chunks-info';
            
            const chunksHeader = document.createElement('div');
            chunksHeader.className = 'chunks-header';
            chunksHeader.innerHTML = `<strong>Source Information:</strong> (${window.lastResponse.chunks.length} chunks used)`;
            chunksDiv.appendChild(chunksHeader);
            
            window.lastResponse.chunks.forEach((chunk, index) => {
                const chunkDiv = document.createElement('div');
                chunkDiv.className = 'chunk-item';
                chunkDiv.innerHTML = `
                    <div class="chunk-header">
                        <span class="chunk-number">Chunk ${index + 1}</span>
                        <span class="relevance-score">Relevance: ${chunk.relevance_score}%</span>
                    </div>
                    <div class="chunk-content">${chunk.content.replace(/\n/g, '<br>')}</div>
                `;
                chunksDiv.appendChild(chunkDiv);
            });
            
            messageDiv.appendChild(chunksDiv);
        }
        
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}); 