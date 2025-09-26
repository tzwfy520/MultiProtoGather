#!/usr/bin/env python3
"""
真实SSH服务器WebSocket终端测试脚本
测试连接到用户提供的SSH服务器 115.190.80.219
"""

import asyncio
import websockets
import json
import requests
import time
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('real_server_test.log')
    ]
)
logger = logging.getLogger(__name__)

class RealServerWebSocketTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000/ws/terminal/"
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
                logger.info("登录成功，获取到JWT token")
                return True
            else:
                logger.error(f"登录失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"登录异常: {e}")
            return False
    
    def get_server_info(self):
        """获取SSH服务器信息"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.base_url}/api/v1/resources/servers/", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                servers = data.get('results', [])
                
                # 查找目标服务器
                target_server = None
                for server in servers:
                    if server.get('ip_address') == '115.190.80.219':
                        target_server = server
                        break
                
                if target_server:
                    self.server_id = target_server['id']
                    logger.info(f"找到目标服务器: {target_server['name']} (ID: {self.server_id})")
                    logger.info(f"服务器详情: {target_server['ip_address']}:{target_server['port']}")
                    return True
                else:
                    logger.error("未找到目标SSH服务器 115.190.80.219")
                    return False
            else:
                logger.error(f"获取服务器列表失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"获取服务器信息异常: {e}")
            return False
    
    async def test_websocket_connection(self):
        """测试WebSocket连接和SSH功能"""
        try:
            # 构建WebSocket URL
            ws_url = f"{self.ws_url}{self.server_id}/?token={self.token}"
            logger.info(f"尝试连接WebSocket: {ws_url}")
            
            # 连接WebSocket
            async with websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                logger.info("WebSocket连接成功！")
                
                # 启动消息接收任务
                receive_task = asyncio.create_task(self.receive_messages(websocket))
                
                # 等待连接稳定
                await asyncio.sleep(3)
                
                # 测试命令列表
                test_commands = [
                    "whoami",
                    "pwd", 
                    "echo 'Hello from WebSocket Terminal!'",
                    "date",
                    "uname -a",
                    "ls -la"
                ]
                
                # 执行测试命令
                for i, command in enumerate(test_commands, 1):
                    logger.info(f"执行测试命令 {i}/{len(test_commands)}: {command}")
                    
                    message = {
                        "type": "command",
                        "data": command + "\n"
                    }
                    
                    await websocket.send(json.dumps(message))
                    await asyncio.sleep(2)  # 等待命令执行
                
                # 测试终端调整大小
                logger.info("测试终端调整大小...")
                resize_message = {
                    "type": "resize",
                    "cols": 120,
                    "rows": 30
                }
                await websocket.send(json.dumps(resize_message))
                await asyncio.sleep(1)
                
                # 等待所有响应
                await asyncio.sleep(5)
                
                # 取消接收任务
                receive_task.cancel()
                
                logger.info("WebSocket测试完成！")
                return True
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"WebSocket连接关闭: {e}")
            return False
        except Exception as e:
            logger.error(f"WebSocket连接异常: {e}")
            return False
    
    async def receive_messages(self, websocket):
        """接收WebSocket消息"""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type', 'unknown')
                    
                    if msg_type == 'output':
                        output = data.get('data', '')
                        if output.strip():
                            logger.info(f"SSH输出: {repr(output)}")
                    elif msg_type == 'error':
                        error_msg = data.get('message', '')
                        logger.error(f"SSH错误: {error_msg}")
                    elif msg_type == 'status':
                        status = data.get('status', '')
                        logger.info(f"连接状态: {status}")
                    else:
                        logger.info(f"收到消息 [{msg_type}]: {data}")
                        
                except json.JSONDecodeError:
                    logger.info(f"收到非JSON消息: {message}")
                    
        except asyncio.CancelledError:
            logger.info("消息接收任务已取消")
        except Exception as e:
            logger.error(f"接收消息异常: {e}")
    
    async def run_test(self):
        """运行完整测试"""
        logger.info("开始真实SSH服务器WebSocket终端测试...")
        
        # 1. 登录
        if not self.login():
            logger.error("登录失败，测试终止")
            return False
        
        # 2. 获取服务器信息
        if not self.get_server_info():
            logger.error("获取服务器信息失败，测试终止")
            return False
        
        # 3. 测试WebSocket连接
        if not await self.test_websocket_connection():
            logger.error("WebSocket连接测试失败")
            return False
        
        logger.info("真实SSH服务器WebSocket终端测试成功！")
        return True

def main():
    """主函数"""
    test = RealServerWebSocketTest()
    
    try:
        result = asyncio.run(test.run_test())
        if result:
            logger.info("所有测试通过！")
            sys.exit(0)
        else:
            logger.error("测试失败！")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()