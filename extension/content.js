function getCaptureData() {
  const selection = window.getSelection();
  let text = selection.toString().trim();
  let links = [];

  if (selection.rangeCount > 0) {
    const range = selection.getRangeAt(0);
    const container = document.createElement('div');
    container.appendChild(range.cloneContents());
    
    // Extract all links within the highlighted selection
    const anchorTags = container.querySelectorAll('a[href]');
    anchorTags.forEach(a => {
      try {
        // Resolve relative URLs to absolute using the page's base URI
        const absoluteUrl = new URL(a.getAttribute('href'), document.baseURI).href;
        links.push(absoluteUrl);
      } catch (e) {
        // Ignore invalid URLs
      }
    });
  }

  // Remove duplicate links
  links = [...new Set(links)];

  return {
    text: text,
    url: window.location.href,
    title: document.title,
    extractedLinks: links
  };
}

getCaptureData();
