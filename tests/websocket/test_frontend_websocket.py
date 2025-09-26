#!/usr/bin/env python3
"""
测试修复后的前端WebSocket连接
"""

import asyncio
import websockets
import json
import requests
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FrontendWebSocketTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000"
        self.token = None
        self.server_id = None
        
    def login(self):
        """登录获取JWT token"""
        try:
            login_data = {
                "username": "admin",
                "password": "admin123"
            }
            response = requests.post(f"{self.base_url}/api/v1/users/login/", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access')
                logger.info("✅ 登录成功，获取到JWT token")
                return True
            else:
                logger.error(f"❌ 登录失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ 登录异常: {e}")
            return False
    
    def get_server_id(self):
        """获取服务器ID"""
        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            response = requests.get(f"{self.base_url}/api/v1/resources/servers/", headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    self.server_id = data['results'][0]['id']
                    logger.info(f"✅ 获取到服务器ID: {self.server_id}")
                    return True
                else:
                    logger.error("❌ 没有找到可用的服务器")
                    return False
            else:
                logger.error(f"❌ 获取服务器列表失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ 获取服务器ID异常: {e}")
            return False
    
    async def test_websocket_connection(self):
        """测试WebSocket连接（模拟前端修复后的连接方式）"""
        try:
            # 使用与前端相同的URL格式，在查询参数中传递token
            ws_url = f"{self.ws_url}/ws/terminal/{self.server_id}/?token={self.token}"
            logger.info(f"🔗 尝试连接WebSocket: {ws_url}")
            
            async with websockets.connect(ws_url) as websocket:
                logger.info("✅ WebSocket连接成功建立")
                
                # 等待初始消息
                try:
                    message_count = 0
                    while message_count < 5:  # 最多接收5条消息
                        message = await asyncio.wait_for(websocket.recv(), timeout=10)
                        data = json.loads(message)
                        msg_type = data.get('type', 'unknown')
                        msg_data = data.get('data', '')
                        
                        logger.info(f"📨 收到消息 [{msg_type}]: {msg_data}")
                        message_count += 1
                        
                        # 如果收到终端就绪消息，发送测试命令
                        if '就绪' in str(msg_data) or 'ready' in str(msg_data).lower():
                            logger.info("🚀 终端就绪，发送测试命令")
                            test_command = {"type": "command", "data": "whoami"}
                            await websocket.send(json.dumps(test_command))
                            
                            # 等待命令响应
                            response = await asyncio.wait_for(websocket.recv(), timeout=10)
                            response_data = json.loads(response)
                            logger.info(f"📨 命令响应: {response_data}")
                            break
                    
                    logger.info("✅ WebSocket终端连接测试成功！")
                    return True
                    
                except asyncio.TimeoutError:
                    logger.warning("⏰ WebSocket消息接收超时")
                    return False
                    
        except websockets.exceptions.InvalidStatusCode as e:
            logger.error(f"❌ WebSocket连接失败 - 状态码: {e.status_code}")
            if e.status_code == 401:
                logger.error("💡 认证失败，可能是JWT令牌无效")
            elif e.status_code == 404:
                logger.error("💡 WebSocket路由未找到")
            return False
            
        except websockets.exceptions.ConnectionRefused:
            logger.error("❌ WebSocket连接被拒绝")
            return False
            
        except Exception as e:
            logger.error(f"❌ WebSocket连接异常: {e}")
            return False
    
    async def run_test(self):
        """运行完整测试"""
        logger.info("🚀 开始前端WebSocket连接测试")
        
        # 1. 登录
        if not self.login():
            return False
        
        # 2. 获取服务器ID
        if not self.get_server_id():
            return False
        
        # 3. 测试WebSocket连接
        result = await self.test_websocket_connection()
        
        if result:
            logger.info("🎉 所有测试通过！前端WebSocket连接修复成功！")
        else:
            logger.error("❌ 测试失败，需要进一步检查")
        
        return result

async def main():
    """主函数"""
    tester = FrontendWebSocketTest()
    await tester.run_test()

if __name__ == "__main__":
    asyncio.run(main())