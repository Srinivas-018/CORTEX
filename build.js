const fs = require('fs');
const path = require('path');

// Recursively find python files
function getPythonFiles(dir, fileList = []) {
  const files = fs.readdirSync(dir);
  files.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    
    // Exclude specific directories to prevent bloating the package
    if (stat.isDirectory()) {
      if (
        file === '.git' || 
        file === 'node_modules' || 
        file === 'dist' || 
        file === 'extracted_evidence' || 
        file === 'deployments' ||
        file === '.streamlit' ||
        file === 'attached_assets'
      ) {
        return;
      }
      getPythonFiles(filePath, fileList);
    } else if (file.endsWith('.py')) {
      fileList.push(filePath);
    }
  });
  return fileList;
}

const rootDir = __dirname;
console.log('Scanning python files in:', rootDir);
const pythonFiles = getPythonFiles(rootDir);

const virtualFiles = {};
pythonFiles.forEach(file => {
  const relPath = path.relative(rootDir, file).replace(/\\/g, '/');
  const content = fs.readFileSync(file);
  const base64 = content.toString('base64');
  virtualFiles[relPath] = base64;
  console.log(`- Bundling virtual file: ${relPath}`);
});

// Construct index.html mounting code
const indexHtmlContent = `<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CORTEX - Mobile Device Forensics Analyzer</title>
    <!-- Load stlite from jsDelivr CDN -->
    <script src="https://cdn.jsdelivr.net/npm/@stlite/mountable@0.76.0/build/stlite.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/mountable@0.76.0/build/style.css" />
    <style>
      body {
        background-color: #0f172a;
        color: #f8fafc;
        font-family: system-ui, -apple-system, sans-serif;
        margin: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100vh;
      }
      .loader-container {
        text-align: center;
      }
      .spinner {
        border: 4px solid rgba(255, 255, 255, 0.1);
        width: 50px;
        height: 50px;
        border-radius: 50%;
        border-left-color: #38bdf8;
        animation: spin 1s linear infinite;
        margin: 0 auto 20px;
      }
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    </style>
  </head>
  <body>
    <div id="root">
      <div class="loader-container">
        <div class="spinner"></div>
        <h2 style="color: #38bdf8;">Initializing CORTEX Forensic Engine...</h2>
        <p style="color: #94a3b8; font-size: 14px;">Loading Python in WebAssembly (this may take 10-15 seconds on first load)</p>
      </div>
    </div>
    <script>
      // Helper function to decode UTF-8 from Base64
      function b64ToUtf8(str) {
        try {
          return decodeURIComponent(escape(atob(str)));
        } catch (e) {
          // Fallback if base64 decoding fails or has special chars
          const binary = atob(str);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
          }
          return new TextDecoder("utf-8").decode(bytes);
        }
      }
      
      // Injected virtual files map (Base64)
      const virtualFiles = ${JSON.stringify(virtualFiles, null, 2)};
      
      const stliteFiles = {};
      for (const [path, b64] of Object.entries(virtualFiles)) {
        stliteFiles[path] = b64ToUtf8(b64);
      }
      
      // Mount Streamlit application using Wasm runtime
      stlite.mount({
        requirements: ["pandas", "plotly", "exifread", "fpdf"],
        entrypoint: "app.py",
        files: stliteFiles,
        // Mount /cortex_data to IndexedDB for persistent case tracking
        idbfsMountpoints: ["/cortex_data"]
      }, document.getElementById("root"));
    </script>
  </body>
</html>`;

// Ensure dist directory exists
const distDir = path.join(rootDir, 'dist');
if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir);
}

fs.writeFileSync(path.join(distDir, 'index.html'), indexHtmlContent);
console.log('Build completed successfully! Web app bundle written to dist/index.html');
