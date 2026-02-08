import os
import time
import asyncio
from typing import Optional
from fastapi import FastAPI, Query, Header, HTTPException
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright

app = FastAPI(
    title="Turnstile Solver (Leapcell)",
    description="Cloudflare Turnstile captcha solver - Serverless Python version",
    version="1.0.0"
)

# Config
API_KEY = os.getenv("API_KEY", "")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
TIMEOUT = int(os.getenv("TIMEOUT", "60"))  # seconds

def log(msg: str):
    if DEBUG:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# Inject Turnstile widget script
def get_inject_script(sitekey: str, action: str = "", cdata: str = "") -> str:
    return f"""
    // Remove existing turnstile widgets
    document.querySelectorAll('.cf-turnstile').forEach(el => el.remove());
    document.querySelectorAll('[data-sitekey]').forEach(el => el.remove());
    
    // Create turnstile container
    const captchaDiv = document.createElement('div');
    captchaDiv.className = 'cf-turnstile';
    captchaDiv.setAttribute('data-sitekey', '{sitekey}');
    {f'captchaDiv.setAttribute("data-action", "{action}");' if action else ''}
    {f'captchaDiv.setAttribute("data-cdata", "{cdata}");' if cdata else ''}
    captchaDiv.style.cssText = 'position:fixed;top:20px;left:20px;z-index:9999;background:white;padding:15px;border:2px solid #0f79af;border-radius:8px;';
    document.body.appendChild(captchaDiv);
    
    // Load Turnstile script
    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
    script.async = true;
    script.onload = function() {{
      setTimeout(() => {{
        if (window.turnstile && window.turnstile.render) {{
          window.turnstile.render(captchaDiv, {{
            sitekey: '{sitekey}',
            {f'action: "{action}",' if action else ''}
            {f'cdata: "{cdata}",' if cdata else ''}
            callback: function(token) {{
              let input = document.querySelector('input[name="cf-turnstile-response"]');
              if (!input) {{
                input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'cf-turnstile-response';
                document.body.appendChild(input);
              }}
              input.value = token;
            }}
          }});
        }}
      }}, 500);
    }};
    document.head.appendChild(script);
    """

# Anti-detection scripts
ANTI_DETECT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
"""

SHADOW_INTERCEPT_SCRIPT = """
(function() {
    const originalAttachShadow = Element.prototype.attachShadow;
    Element.prototype.attachShadow = function(init) {
        const shadow = originalAttachShadow.call(this, init);
        if (init.mode === 'closed') window.__lastClosedShadowRoot = shadow;
        return shadow;
    };
})();
"""

async def solve_turnstile(url: str, sitekey: str, action: str = "", cdata: str = "") -> dict:
    """Solve Turnstile captcha"""
    start_time = time.time()
    
    log(f"Starting solve for {url} with sitekey {sitekey}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--single-process',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-zygote',
            ]
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 500, 'height': 300}
        )
        
        page = await context.new_page()
        
        # Add anti-detection scripts
        await page.add_init_script(SHADOW_INTERCEPT_SCRIPT)
        await page.add_init_script(ANTI_DETECT_SCRIPT)
        
        # Block unnecessary resources
        async def route_handler(route):
            resource_type = route.request.resource_type
            url_str = route.request.url
            
            if resource_type in ['document', 'script', 'xhr', 'fetch']:
                await route.continue_()
            elif 'cloudflare.com' in url_str:
                await route.continue_()
            else:
                await route.abort()
        
        await page.route("**/*", route_handler)
        
        try:
            log(f"Navigating to {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            log("Injecting Turnstile widget")
            await page.evaluate(get_inject_script(sitekey, action, cdata))
            
            # Wait for widget to load
            await asyncio.sleep(3)
            
            # Poll for token
            max_attempts = TIMEOUT - int(time.time() - start_time)
            log(f"Waiting for token (max {max_attempts}s)")
            
            for attempt in range(max_attempts):
                try:
                    token = await page.evaluate("""
                        () => {
                            const input = document.querySelector('input[name="cf-turnstile-response"]');
                            return input ? input.value : null;
                        }
                    """)
                    
                    if token:
                        elapsed = round(time.time() - start_time, 2)
                        log(f"Token found in {elapsed}s: {token[:20]}...")
                        return {"token": token, "elapsed": elapsed}
                    
                    # Try clicking checkbox
                    if attempt % 3 == 0:
                        try:
                            frame = page.frame_locator('iframe[src*="challenges.cloudflare.com"]')
                            checkbox = frame.locator('input[type="checkbox"]')
                            if await checkbox.count() > 0:
                                await checkbox.click(timeout=1000)
                                log("Clicked checkbox")
                        except:
                            pass
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    log(f"Attempt {attempt + 1} error: {e}")
            
            raise Exception("Timeout: Could not solve captcha")
            
        finally:
            await browser.close()


@app.get("/")
async def root():
    return {
        "name": "Turnstile Solver (Leapcell Python)",
        "version": "1.0.0",
        "description": "Cloudflare Turnstile captcha solver - Playwright + Chromium",
        "endpoints": {
            "GET /turnstile": {
                "description": "Solve Turnstile captcha (synchronous)",
                "params": {
                    "url": "string (required) - Target page URL",
                    "sitekey": "string (required) - Turnstile sitekey",
                    "action": "string (optional) - Action parameter",
                    "cdata": "string (optional) - Custom data parameter"
                }
            },
            "GET /health": "Health check"
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "turnstile-solver", "version": "1.0.0-playwright"}


@app.get("/turnstile")
async def solve(
    url: str = Query(..., description="Target page URL"),
    sitekey: str = Query(..., description="Turnstile sitekey"),
    action: Optional[str] = Query(None, description="Action parameter"),
    cdata: Optional[str] = Query(None, description="Custom data parameter"),
    x_api_key: Optional[str] = Header(None),
    key: Optional[str] = Query(None)
):
    # Auth check
    if API_KEY and x_api_key != API_KEY and key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        log(f"Request: url={url}, sitekey={sitekey}")
        
        result = await solve_turnstile(url, sitekey, action or "", cdata or "")
        
        return JSONResponse({
            "errorId": 0,
            "status": "ready",
            "solution": {
                "token": result["token"]
            },
            "elapsed": result["elapsed"]
        })
        
    except Exception as e:
        print(f"Solve error: {e}")
        return JSONResponse(
            status_code=500,
            content={"errorId": 1, "error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
