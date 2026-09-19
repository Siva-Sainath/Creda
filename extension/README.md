# Creda Chrome extension

## Load unpacked (no Web Store)

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select this `extension/` folder

## Supported careers pages

On **Greenhouse**, **Lever**, **Ashby**, or employer job pages (e.g. `stripe.com/jobs`), Creda captures:

- Page URL and ATS job links (`gh_jid`, Lever UUID, Ashby UUID)
- Job title from the page heading
- Page text when nothing is selected

## Use

1. Open Gmail, LinkedIn, a careers page, or any page with a recruitment message
2. Select the suspicious text
3. Click the **Creda** extension icon
4. Review captured text, crop the screenshot if needed
5. Click **Check with Creda**

Results poll the Mumbai API and show verdict + evidence in the side panel.

## Configuration

Edit `config.js` to point at another API or UI base URL.
