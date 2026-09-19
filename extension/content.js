function getCaptureData() {
  const page = typeof buildPageContext === 'function' ? buildPageContext() : null;
  const selection = window.getSelection();
  let text = selection.toString().trim();
  let links = [];

  if (selection.rangeCount > 0) {
    const range = selection.getRangeAt(0);
    const container = document.createElement('div');
    container.appendChild(range.cloneContents());
    container.querySelectorAll('a[href]').forEach((a) => {
      try { links.push(new URL(a.getAttribute('href'), document.baseURI).href); } catch (e) {}
    });
  }

  if (page) {
    if (!text && page.snippet) text = page.snippet;
    if (!text && page.title) text = page.title;
    links = [...new Set([...links, ...(page.jobLinks || []), page.url])];
  }

  return {
    text,
    url: window.location.href,
    title: document.title,
    extractedLinks: [...new Set(links)],
    pageContext: page,
  };
}

let modalIframe = null;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "toggleModal") {
    // If it's already open, toggle it off
    if (modalIframe) {
      modalIframe.remove();
      modalIframe = null;
      return;
    }

    const data = getCaptureData();
    
    // Save to storage so the iframe can load it
    chrome.storage.local.set({
      captureData: {
        text: data.text,
        url: data.url,
        extractedLinks: data.extractedLinks,
        screenshot: request.screenshot
      }
    }, () => {
      // Inject iframe
      modalIframe = document.createElement('iframe');
      modalIframe.id = "creda-floating-modal";
      modalIframe.src = chrome.runtime.getURL('investigate.html');
      modalIframe.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        width: 1000px;
        max-width: 90vw;
        height: 600px;
        max-height: 90vh;
        border: none;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        z-index: 2147483647;
        background: white;
      `;
      document.body.appendChild(modalIframe);
    });
  }
});

// Listen for message from iframe to close itself
window.addEventListener("message", (event) => {
  if (event.data === "closeModal" && modalIframe) {
    modalIframe.remove();
    modalIframe = null;
  }
});
