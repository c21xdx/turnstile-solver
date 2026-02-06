"""
Turnstile Solver 客户端库

可以直接复制到其他项目中使用
"""

import time
import requests
from typing import Optional


class TurnstileSolver:
    """
    Turnstile Solver 客户端
    
    示例:
        solver = TurnstileSolver("http://127.0.0.1:5072")
        token = solver.solve(
            url="https://example.com",
            sitekey="0x4AAAAAAxxxxxx"
        )
    """
    
    def __init__(self, server_url: str = "http://127.0.0.1:5072"):
        self.server_url = server_url.rstrip('/')
    
    def create_task(self, url: str, sitekey: str) -> str:
        """创建 Turnstile 解决任务"""
        resp = requests.post(
            f"{self.server_url}/createTask",
            json={
                "websiteURL": url,
                "websiteKey": sitekey
            },
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        if 'error' in data:
            raise Exception(f"Create task failed: {data['error']}")
        
        return data['taskId']
    
    def get_result(self, task_id: str) -> dict:
        """获取任务结果"""
        resp = requests.post(
            f"{self.server_url}/getTaskResult",
            json={"taskId": task_id},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()
    
    def solve(self, url: str, sitekey: str, timeout: int = 60, poll_interval: float = 2) -> Optional[str]:
        """
        解决 Turnstile 验证码
        
        Args:
            url: 网站 URL
            sitekey: Turnstile site key
            timeout: 超时时间(秒)
            poll_interval: 轮询间隔(秒)
        
        Returns:
            Turnstile token 或 None
        
        Raises:
            Exception: 解决失败时抛出异常
        """
        # 创建任务
        task_id = self.create_task(url, sitekey)
        
        # 等待结果
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.get_result(task_id)
            status = result.get('status')
            
            if status == 'ready':
                token = result.get('solution', {}).get('token')
                return token
            elif status == 'failed':
                error = result.get('error', 'Unknown error')
                raise Exception(f"Turnstile solve failed: {error}")
            
            time.sleep(poll_interval)
        
        raise Exception(f"Turnstile solve timeout ({timeout}s)")
    
    def health(self) -> dict:
        """检查服务健康状态"""
        resp = requests.get(f"{self.server_url}/health", timeout=5)
        resp.raise_for_status()
        return resp.json()


# 兼容旧版 API 的客户端
class TurnstileSolverLegacy:
    """旧版 API 客户端 (兼容 grok 项目)"""
    
    def __init__(self, server_url: str = "http://127.0.0.1:5072"):
        self.server_url = server_url.rstrip('/')
    
    def create_task(self, url: str, sitekey: str) -> str:
        resp = requests.get(
            f"{self.server_url}/turnstile",
            params={"url": url, "sitekey": sitekey},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()['taskId']
    
    def get_response(self, task_id: str, max_retries: int = 30, initial_delay: float = 5, retry_delay: float = 2) -> Optional[str]:
        time.sleep(initial_delay)
        
        for _ in range(max_retries):
            try:
                resp = requests.get(
                    f"{self.server_url}/result",
                    params={"id": task_id},
                    timeout=10
                )
                resp.raise_for_status()
                data = resp.json()
                token = data.get('solution', {}).get('token')
                
                if token and token != 'CAPTCHA_FAIL':
                    return token
                elif token == 'CAPTCHA_FAIL':
                    return None
                
                time.sleep(retry_delay)
            except Exception as e:
                time.sleep(retry_delay)
        
        return None


if __name__ == '__main__':
    # 测试
    solver = TurnstileSolver()
    
    print("检查服务状态...")
    try:
        health = solver.health()
        print(f"服务状态: {health}")
    except Exception as e:
        print(f"服务不可用: {e}")
        print("\n请先启动服务: python solver.py")
