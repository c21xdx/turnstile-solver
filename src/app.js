const express = require('express');
const puppeteer = require('puppeteer');
const proxyChain = require('proxy-chain');

const app = express();
app.use(express.json());

// Config
const API_KEY = process.env.API_KEY || '';
const DEBUG = process.env.DEBUG === 'true';
const TIMEOUT = parseInt(process.env.TIMEOUT) || 90000;
const DEFAULT_PROXY = process.env.PROXY || '';

function log(msg) {
  if (DEBUG) console.log(`[${new Date().toISOString()}] ${msg}`);
}

// Browser config
function getBrowserConfig() {
  const versions = ['120.0.0.0', '121.0.0.0', '122.0.0.0', '124.0.0.0'];
  const version = versions[Math.floor(Math.random() * versions.length)];
  const majorVersion = version.split('.')[0];
  
  return {
    version,
    userAgent: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${version} Safari/537.36`,
    secChUa: `"Not(A:Brand";v="99", "Google Chrome";v="${majorVersion}", "Chromium";v="${majorVersion}"`
  };
}

// Auth middleware
function authMiddleware(req, res, next) {
  if (!API_KEY) return next();
  const key = req.headers['x-api-key'] || req.query.key;
  if (key === API_KEY) return next();
  return res.status(401).json({ errorId: 1, error: 'Unauthorized' });
}

// Inject Turnstile widget
function getInjectScript(sitekey, action, cdata) {
  return `
    document.querySelectorAll('.cf-turnstile').forEach(el => el.remove());
    document.querySelectorAll('[data-sitekey]').forEach(el => el.remove());
    
    const captchaDiv = document.createElement('div');
    captchaDiv.className = 'cf-turnstile';
    captchaDiv.setAttribute('data-sitekey', '${sitekey}');
    ${action ? `captchaDiv.setAttribute('data-action', '${action}');` : ''}
    ${cdata ? `captchaDiv.setAttribute('data-cdata', '${cdata}');` : ''}
    captchaDiv.style.cssText = 'position:fixed;top:20px;left:20px;z-index:9999;background:white;padding:15px;border:2px solid #0f79af;border-radius:8px;';
    document.body.appendChild(captchaDiv);
    
    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
    script.async = true;
    script.onload = function() {
      setTimeout(() => {
        if (window.turnstile && window.turnstile.render) {
          window.turnstile.render(captchaDiv, {
            sitekey: '${sitekey}',
            ${action ? `action: '${action}',` : ''}
            ${cdata ? `cdata: '${cdata}',` : ''}
            callback: function(token) {
              let input = document.querySelector('input[name="cf-turnstile-response"]');
              if (!input) {
                input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'cf-turnstile-response';
                document.body.appendChild(input);
              }
              input.value = token;
            }
          });
        }
      }, 500);
    };
    document.head.appendChild(script);
  `;
}

// Find and click checkbox
async function findAndClickCheckbox(page) {
  const iframeSelectors = [
    'iframe[src*="challenges.cloudflare.com"]',
    'iframe[src*="turnstile"]',
    'iframe[title*="widget"]'
  ];
  
  for (const iframeSelector of iframeSelectors) {
    try {
      const iframes = await page.$$(iframeSelector);
      if (iframes.length === 0) continue;
      
      for (const iframe of iframes) {
        try {
          const frame = await iframe.contentFrame();
          if (!frame) continue;
          
          const checkboxSelectors = [
            'input[type="checkbox"]',
            '.cb-lb input[type="checkbox"]',
            'label input[type="checkbox"]'
          ];
          
          for (const cbSelector of checkboxSelectors) {
            try {
              const checkbox = await frame.$(cbSelector);
              if (checkbox) {
                await checkbox.click();
                log(`Clicked checkbox: ${cbSelector}`);
                return true;
              }
            } catch (e) {}
          }
          
          try {
            const box = await iframe.boundingBox();
            if (box) {
              await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
              log('Clicked iframe center');
              return true;
            }
          } catch (e) {}
        } catch (e) {}
      }
    } catch (e) {}
  }
  
  return false;
}

// Solve Turnstile
async function solveTurnstile(url, sitekey, action, cdata, proxyStr) {
  const startTime = Date.now();
  let browser = null;
  let anonymizedProxy = null;
  
  const config = getBrowserConfig();
  const originalProxy = proxyStr || DEFAULT_PROXY;
  
  log(`Using Chrome ${config.version}`);
  if (originalProxy) log(`Using proxy: ${originalProxy}`);
  
  try {
    const launchOptions = {
      headless: true,
      args: [
        '--single-process',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-gpu',
        '--no-zygote',
        '--disable-dev-shm-usage',
        '--disable-blink-features=AutomationControlled',
        `--user-agent=${config.userAgent}`,
      ],
      executablePath: './google-chrome-stable',
      timeout: 60000,
    };
    
    // Handle proxy (supports HTTP, HTTPS, SOCKS4, SOCKS5)
    if (originalProxy) {
      // proxy-chain anonymizes the proxy (handles auth and converts SOCKS to HTTP)
      anonymizedProxy = await proxyChain.anonymizeProxy(originalProxy);
      log(`Anonymized proxy: ${anonymizedProxy}`);
      launchOptions.args.push(`--proxy-server=${anonymizedProxy}`);
    }
    
    browser = await puppeteer.launch(launchOptions);
    const page = await browser.newPage();
    
    await page.setViewport({ width: 500, height: 300 });
    
    await page.setExtraHTTPHeaders({
      'sec-ch-ua': config.secChUa,
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"Windows"',
      'Accept-Language': 'en-US,en;q=0.9',
    });
    
    // Anti-detection
    await page.evaluateOnNewDocument(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
      delete navigator.__proto__.webdriver;
      window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
      Object.defineProperty(navigator, 'plugins', { 
        get: () => {
          const plugins = [1, 2, 3, 4, 5];
          plugins.item = (i) => plugins[i];
          plugins.namedItem = () => null;
          plugins.refresh = () => {};
          return plugins;
        }
      });
      Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
      Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
      Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
      Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
      
      const originalQuery = window.navigator.permissions.query;
      window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
          Promise.resolve({ state: Notification.permission }) :
          originalQuery(parameters)
      );
      
      const getParameter = WebGLRenderingContext.prototype.getParameter;
      WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.call(this, parameter);
      };
    });
    
    log(`Navigating to ${url}`);
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    
    log('Injecting Turnstile widget');
    await page.evaluate(getInjectScript(sitekey, action, cdata));
    
    await new Promise(r => setTimeout(r, 3000));
    
    const maxAttempts = Math.floor((TIMEOUT - (Date.now() - startTime)) / 1000);
    log(`Waiting for token (max ${maxAttempts}s)`);
    
    let clickCount = 0;
    const maxClicks = 5;
    
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const token = await page.evaluate(() => {
          const input = document.querySelector('input[name="cf-turnstile-response"]');
          return input ? input.value : null;
        });
        
        if (token) {
          const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
          log(`Token found in ${elapsed}s`);
          return { token, elapsed: parseFloat(elapsed) };
        }
        
        if (attempt % 3 === 0 && clickCount < maxClicks) {
          const clicked = await findAndClickCheckbox(page);
          if (clicked) clickCount++;
        }
        
        await new Promise(r => setTimeout(r, 1000));
      } catch (e) {
        log(`Attempt ${attempt + 1} error: ${e.message}`);
      }
    }
    
    throw new Error('Timeout: Could not solve captcha');
    
  } finally {
    if (browser) await browser.close().catch(() => {});
    // Close anonymized proxy server
    if (anonymizedProxy) await proxyChain.closeAnonymizedProxy(anonymizedProxy, true).catch(() => {});
  }
}

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'turnstile-solver', version: '1.0.2-socks5' });
});

// API docs
app.get('/', (req, res) => {
  res.json({
    name: 'Turnstile Solver (Leapcell)',
    version: '1.0.2',
    description: 'Cloudflare Turnstile solver with HTTP/SOCKS5 proxy support',
    endpoints: {
      'GET /turnstile': {
        params: {
          url: 'string (required)',
          sitekey: 'string (required)',
          action: 'string (optional)',
          cdata: 'string (optional)',
          proxy: 'string (optional)'
        }
      }
    },
    proxyFormats: [
      'http://ip:port',
      'http://user:pass@ip:port',
      'socks5://ip:port',
      'socks5://user:pass@ip:port',
      'socks4://ip:port'
    ]
  });
});

// Solve endpoint
app.get('/turnstile', authMiddleware, async (req, res) => {
  const { url, sitekey, action, cdata, proxy } = req.query;
  
  if (!url || !sitekey) {
    return res.status(400).json({ errorId: 1, error: 'Missing url or sitekey' });
  }
  
  try {
    log(`Request: url=${url}, sitekey=${sitekey}, proxy=${proxy || DEFAULT_PROXY || 'none'}`);
    
    const result = await solveTurnstile(url, sitekey, action || '', cdata || '', proxy);
    
    res.json({
      errorId: 0,
      status: 'ready',
      solution: { token: result.token },
      elapsed: result.elapsed
    });
    
  } catch (error) {
    console.error('Solve error:', error.message);
    res.status(500).json({ errorId: 1, error: error.message });
  }
});

const port = process.env.PORT || 8080;
app.listen(port, () => {
  console.log(`Turnstile Solver running on port ${port}`);
  console.log(`Default proxy: ${DEFAULT_PROXY || 'none'}`);
});
