"""
Turnstile Solver - 独立的 Cloudflare Turnstile 验证码解决服务

使用 Camoufox 浏览器自动解决 Turnstile 验证码，提供 HTTP API 供其他项目调用。

API:
    POST /createTask
        {"websiteURL": "https://example.com", "websiteKey": "0x4AAA..."}
        返回: {"taskId": "xxx"}
    
    POST /getTaskResult  
        {"taskId": "xxx"}
        返回: {"status": "ready", "solution": {"token": "xxx"}}
    
    兼容旧版 API:
    GET /turnstile?url=xxx&sitekey=xxx
    GET /result?id=xxx

用法:
    python solver.py --port 5072 --thread 2
"""

import os
import sys
import time
import uuid
import random
import logging
import asyncio
import argparse
from typing import Optional
from quart import Quart, request, jsonify
from camoufox.async_api import AsyncCamoufox

# ================= 配置 =================
DEFAULT_PORT = 5072
DEFAULT_THREADS = 2
DEFAULT_TIMEOUT = 60

# ================= 日志 =================
class ColorLogger:
    COLORS = {
        'DEBUG': '\033[35m',
        'INFO': '\033[34m', 
        'SUCCESS': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'RESET': '\033[0m',
    }
    
    @staticmethod
    def log(level, message):
        timestamp = time.strftime('%H:%M:%S')
        color = ColorLogger.COLORS.get(level, '')
        reset = ColorLogger.COLORS['RESET']
        print(f"[{timestamp}] [{color}{level}{reset}] {message}")
    
    @staticmethod
    def info(msg): ColorLogger.log('INFO', msg)
    @staticmethod
    def success(msg): ColorLogger.log('SUCCESS', msg)
    @staticmethod
    def warning(msg): ColorLogger.log('WARNING', msg)
    @staticmethod
    def error(msg): ColorLogger.log('ERROR', msg)
    @staticmethod
    def debug(msg): ColorLogger.log('DEBUG', msg)

logger = ColorLogger()

# ================= 内存数据库 =================
results_db = {}

async def save_result(task_id: str, data: dict):
    results_db[task_id] = {
        **data,
        'createTime': time.time()
    }

async def load_result(task_id: str) -> Optional[dict]:
    return results_db.get(task_id)

async def cleanup_old_results(max_age: int = 300):
    """清理超过 max_age 秒的结果"""
    now = time.time()
    to_delete = [tid for tid, res in results_db.items() 
                 if now - res.get('createTime', now) > max_age]
    for tid in to_delete:
        del results_db[tid]
    return len(to_delete)

# ================= Turnstile Solver =================
class TurnstileSolver:
    def __init__(self, headless: bool = True, thread_count: int = DEFAULT_THREADS, debug: bool = False):
        self.headless = headless
        self.thread_count = thread_count
        self.debug = debug
        self.browser_pool = asyncio.Queue()
        self.app = Quart(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """设置 API 路由"""
        
        # 新版 API - POST /createTask
        @self.app.route('/createTask', methods=['POST'])
        async def create_task():
            try:
                data = await request.get_json()
                url = data.get('websiteURL') or data.get('url')
                sitekey = data.get('websiteKey') or data.get('sitekey')
                
                if not url or not sitekey:
                    return jsonify({'error': 'Missing websiteURL or websiteKey'}), 400
                
                task_id = str(uuid.uuid4())
                await save_result(task_id, {'status': 'processing', 'value': None})
                
                asyncio.create_task(self._solve_turnstile(task_id, url, sitekey))
                
                return jsonify({'taskId': task_id})
            except Exception as e:
                logger.error(f"createTask error: {e}")
                return jsonify({'error': str(e)}), 500
        
        # 新版 API - POST /getTaskResult
        @self.app.route('/getTaskResult', methods=['POST'])
        async def get_task_result():
            try:
                data = await request.get_json()
                task_id = data.get('taskId')
                
                if not task_id:
                    return jsonify({'error': 'Missing taskId'}), 400
                
                result = await load_result(task_id)
                if not result:
                    return jsonify({'error': 'Task not found'}), 404
                
                status = result.get('status', 'processing')
                token = result.get('value')
                
                if status == 'ready' and token:
                    return jsonify({
                        'status': 'ready',
                        'solution': {'token': token}
                    })
                elif status == 'failed':
                    return jsonify({
                        'status': 'failed',
                        'error': result.get('error', 'Unknown error')
                    })
                else:
                    return jsonify({'status': 'processing'})
            except Exception as e:
                logger.error(f"getTaskResult error: {e}")
                return jsonify({'error': str(e)}), 500
        
        # 兼容旧版 API - GET /turnstile
        @self.app.route('/turnstile', methods=['GET'])
        async def turnstile_legacy():
            url = request.args.get('url')
            sitekey = request.args.get('sitekey')
            
            if not url or not sitekey:
                return jsonify({'error': 'Missing url or sitekey'}), 400
            
            task_id = str(uuid.uuid4())
            await save_result(task_id, {'status': 'processing', 'value': None})
            
            asyncio.create_task(self._solve_turnstile(task_id, url, sitekey))
            
            return jsonify({'taskId': task_id})
        
        # 兼容旧版 API - GET /result
        @self.app.route('/result', methods=['GET'])
        async def result_legacy():
            task_id = request.args.get('id')
            
            if not task_id:
                return jsonify({'error': 'Missing id'}), 400
            
            result = await load_result(task_id)
            if not result:
                return jsonify({'error': 'Task not found'}), 404
            
            token = result.get('value')
            if token and token != 'CAPTCHA_FAIL':
                return jsonify({'solution': {'token': token}})
            elif token == 'CAPTCHA_FAIL':
                return jsonify({'solution': {'token': 'CAPTCHA_FAIL'}})
            else:
                return jsonify({'solution': {'token': None}})
        
        # 健康检查
        @self.app.route('/health', methods=['GET'])
        async def health():
            return jsonify({
                'status': 'ok',
                'pool_size': self.browser_pool.qsize(),
                'pending_tasks': len([r for r in results_db.values() if r.get('status') == 'processing'])
            })
    
    async def _solve_turnstile(self, task_id: str, url: str, sitekey: str):
        """解决 Turnstile 验证码"""
        browser = None
        try:
            # 从池中获取浏览器
            browser = await asyncio.wait_for(self.browser_pool.get(), timeout=30)
            
            if self.debug:
                logger.debug(f"Task {task_id[:8]}... solving for {url}")
            
            page = await browser.new_page()
            
            try:
                # 构造包含 Turnstile 的页面
                html_content = f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
                </head>
                <body>
                    <div class="cf-turnstile" data-sitekey="{sitekey}" data-callback="onSuccess"></div>
                    <script>
                        function onSuccess(token) {{
                            window.turnstileToken = token;
                        }}
                    </script>
                </body>
                </html>
                '''
                
                # 设置页面内容
                await page.set_content(html_content)
                await page.wait_for_load_state('networkidle')
                
                # 等待 Turnstile 完成
                token = None
                for _ in range(DEFAULT_TIMEOUT):
                    token = await page.evaluate('window.turnstileToken')
                    if token:
                        break
                    await asyncio.sleep(1)
                
                if token:
                    logger.success(f"Task {task_id[:8]}... solved")
                    await save_result(task_id, {'status': 'ready', 'value': token})
                else:
                    logger.warning(f"Task {task_id[:8]}... timeout")
                    await save_result(task_id, {'status': 'failed', 'value': 'CAPTCHA_FAIL', 'error': 'Timeout'})
            
            finally:
                await page.close()
        
        except asyncio.TimeoutError:
            logger.error(f"Task {task_id[:8]}... no browser available")
            await save_result(task_id, {'status': 'failed', 'value': 'CAPTCHA_FAIL', 'error': 'No browser available'})
        except Exception as e:
            logger.error(f"Task {task_id[:8]}... error: {e}")
            await save_result(task_id, {'status': 'failed', 'value': 'CAPTCHA_FAIL', 'error': str(e)})
        finally:
            if browser:
                await self.browser_pool.put(browser)
    
    async def _init_browser_pool(self):
        """初始化浏览器池"""
        logger.info(f"Initializing {self.thread_count} browser(s)...")
        
        for i in range(self.thread_count):
            try:
                browser = await AsyncCamoufox(headless=self.headless).__aenter__()
                await self.browser_pool.put(browser)
                if self.debug:
                    logger.debug(f"Browser {i+1} ready")
            except Exception as e:
                logger.error(f"Failed to init browser {i+1}: {e}")
        
        logger.success(f"Browser pool ready: {self.browser_pool.qsize()} browser(s)")
    
    async def _cleanup_loop(self):
        """定期清理旧结果"""
        while True:
            await asyncio.sleep(60)
            cleaned = await cleanup_old_results(300)
            if cleaned > 0 and self.debug:
                logger.debug(f"Cleaned {cleaned} old results")
    
    def run(self, host: str = '0.0.0.0', port: int = DEFAULT_PORT):
        """启动服务"""
        @self.app.before_serving
        async def startup():
            await self._init_browser_pool()
            asyncio.create_task(self._cleanup_loop())
        
        print("\n" + "=" * 50)
        print("  Turnstile Solver")
        print("=" * 50)
        print(f"  API: http://{host}:{port}")
        print(f"  Browsers: {self.thread_count}")
        print(f"  Headless: {self.headless}")
        print("=" * 50 + "\n")
        
        self.app.run(host=host, port=port)


def main():
    parser = argparse.ArgumentParser(description='Turnstile Solver Service')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help=f'Port (default: {DEFAULT_PORT})')
    parser.add_argument('--thread', type=int, default=DEFAULT_THREADS, help=f'Browser count (default: {DEFAULT_THREADS})')
    parser.add_argument('--host', default='0.0.0.0', help='Host (default: 0.0.0.0)')
    parser.add_argument('--headed', action='store_true', help='Run with visible browser')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    
    args = parser.parse_args()
    
    solver = TurnstileSolver(
        headless=not args.headed,
        thread_count=args.thread,
        debug=args.debug
    )
    
    solver.run(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
