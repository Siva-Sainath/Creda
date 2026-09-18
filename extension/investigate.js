let cropper = null;
let currentCaseId = null;
let currentToken = null;
let pollInterval = null;

document.addEventListener('DOMContentLoaded', async () => {
  // Hide new tab button if we are already in a top-level tab
  if (window.self === window.top) {
    const btnNewTab = document.getElementById('btn-new-tab');
    if (btnNewTab) btnNewTab.style.display = 'none';
  }

  // Hide the results panel initially so Step 1 takes full width
  document.querySelector('.result-panel').style.display = 'none';

  document.getElementById('btn-close').addEventListener('click', () => {
    if (window.self !== window.top) {
      parent.postMessage("closeModal", "*");
    } else {
      window.close();
    }
  });
  // Load data from storage passed by the background script
  chrome.storage.local.get(['captureData'], (result) => {
    const data = result.captureData;
    if (!data) return;

    if (data.text) document.getElementById('captured-text').value = data.text;
    
    let allLinks = [data.url];
    if (data.extractedLinks && data.extractedLinks.length > 0) {
      allLinks = allLinks.concat(data.extractedLinks);
    }
    if (allLinks.length > 0) document.getElementById('captured-url').value = allLinks.join(', ');

    if (data.screenshot) {
      const img = document.getElementById('screenshot-image');
      img.src = data.screenshot;
      img.onload = () => {
        cropper = new Cropper(img, {
          viewMode: 1,
          autoCropArea: 0.8,
          background: false
        });
      };
    }
  });
});

document.getElementById('btn-check').addEventListener('click', () => {
  const text = document.getElementById('captured-text').value;
  const urlString = document.getElementById('captured-url').value;
  
  if (!text && !cropper) {
    alert("Please ensure there is text or an image.");
    return;
  }
  
  showView('loading-view');
  
  // 1. Hide the input panel and show the result panel
  document.querySelector('.input-panel').style.display = 'none';
  document.querySelector('.result-panel').style.display = 'flex';
  
  // Get cropped image data URL
  const screenshotDataUrl = cropper ? cropper.getCroppedCanvas().toDataURL('image/jpeg', 0.8) : null;
  
  // Parse links back into an array
  const linksArray = urlString.split(',').map(l => l.trim()).filter(l => l);
  
  const payload = {
    text: text,
    links: linksArray,
    locale: "en-IN",
    screenshotDataUrl: screenshotDataUrl
  };
  
  chrome.runtime.sendMessage({ action: 'submitCase', payload }, response => {
    if (response && response.success) {
      currentCaseId = response.data.caseId;
      currentToken = response.data.accessToken;
      startPolling();
    } else {
      document.getElementById('loading-status').innerText = `Error: ${response?.error || 'Unknown error'}`;
    }
  });
});

function startPolling() {
  pollInterval = setInterval(() => {
    chrome.runtime.sendMessage({ 
      action: 'pollCase', 
      caseId: currentCaseId, 
      token: currentToken 
    }, response => {
      if (response && response.success) {
        handleStatusUpdate(response.data);
      } else {
        document.getElementById('loading-status').innerText = `Error: ${response?.error || 'Polling failed'}`;
      }
    });
  }, 2500);
}

function handleStatusUpdate(data) {
  if (data.status === 'completed' || data.status === 'needs_evidence' || data.status === 'could_not_complete') {
    clearInterval(pollInterval);
    renderResult(data);
    showView('result-view');
  } else {
    document.getElementById('loading-status').innerText = data.stage || 'Checking...';
  }
}

function renderResult(data) {
  const banner = document.getElementById('verdict-banner');
  const title = document.getElementById('verdict-title');
  const headline = document.getElementById('verdict-headline');
  
  banner.className = 'vchip';
  if (data.verdict === 'high_risk') banner.classList.add('r');
  else if (data.verdict === 'no_conflict_found') banner.classList.add('g');
  else banner.classList.add('c');
  
  title.innerText = data.verdict ? data.verdict.replace('_', ' ').toUpperCase() : 'UNKNOWN';
  headline.innerText = data.headline || '';
  
  const evidenceList = document.getElementById('evidence-list');
  evidenceList.innerHTML = '';
  
  if (data.evidence && data.evidence.length > 0) {
    data.evidence.forEach(ev => {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `
        <div class="card-title">
          <span>${ev.check.replace('_', ' ')}</span>
          <span class="tier-badge">T${ev.tier}</span>
        </div>
        <div class="card-source">${ev.sourceUrl || 'Internal Check'}</div>
        <div class="card-excerpt">${ev.excerpt || ''}</div>
      `;
      evidenceList.appendChild(card);
    });
  }
}

function showView(viewId) {
  document.querySelectorAll('.result-panel .view').forEach(v => v.classList.remove('active'));
  document.getElementById(viewId).classList.add('active');
}
