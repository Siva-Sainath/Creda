// Hardcoded for local dev or placeholder for API Gateway
const API_BASE_URL = 'http://127.0.0.1:3000'; // Routing to local SAM API

chrome.action.onClicked.addListener(async (tab) => {
  if (tab.url.startsWith('chrome://')) return;

  try {
    // 1. Capture screen immediately
    const screenshotDataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'jpeg', quality: 90 });
    
    // 2. Ask content script to extract text, url and display the floating modal
    try {
      await chrome.tabs.sendMessage(tab.id, { 
        action: "toggleModal", 
        screenshot: screenshotDataUrl 
      });
    } catch (e) {
      // If content script isn't loaded yet (e.g. tab was open before extension installed), inject it first
      console.log("Content script not found, injecting dynamically...");
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['content.js']
      });
      // Try sending the message again after injection
      await chrome.tabs.sendMessage(tab.id, { 
        action: "toggleModal", 
        screenshot: screenshotDataUrl 
      });
    }

  } catch (err) {
    console.error("Capture failed:", err);
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'submitCase') {
    submitToBackend(message.payload)
      .then(data => sendResponse({ success: true, data }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep the messaging channel open for async response
  }
  
  if (message.action === 'pollCase') {
    pollBackend(message.caseId, message.token)
      .then(data => sendResponse({ success: true, data }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; 
  }
});

async function submitToBackend(payload) {
  let screenshotKey = null;

  if (payload.screenshotDataUrl) {
    // 1. Get presigned URL
    const uploadUrlResponse = await fetch(`${API_BASE_URL}/upload-url`, { method: 'POST' });
    if (!uploadUrlResponse.ok) throw new Error("Failed to get upload URL");
    const { uploadUrl, key } = await uploadUrlResponse.json();
    
    // 2. Convert base64 to blob and upload
    const blob = await (await fetch(payload.screenshotDataUrl)).blob();
    const putResponse = await fetch(uploadUrl, {
      method: 'PUT',
      headers: { 'Content-Type': 'image/jpeg' },
      body: blob
    });
    
    if (!putResponse.ok) throw new Error("Failed to upload screenshot");
    screenshotKey = key;
  }

  // 3. Submit case
  const casePayload = {
    text: payload.text,
    links: payload.links,
    locale: payload.locale,
    screenshotKey: screenshotKey
  };

  const response = await fetch(`${API_BASE_URL}/cases`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(casePayload)
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  
  return await response.json(); // expected: { caseId, accessToken, status }
}

async function pollBackend(caseId, token) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'X-Case-Token': token
    }
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  
  return await response.json();
}
