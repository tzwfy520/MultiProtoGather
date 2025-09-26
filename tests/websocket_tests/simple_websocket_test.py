#!/usr/bin/env python3
"""
简化的WebSocket终端测试脚本
专门测试真实SSH连接功能
"""

import asyncio
import websockets
import json
import requests
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleWebSocketTester:
    """简化的WebSocket终端测试器"""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.ws_url = "ws://127.0.0.1:8000"
        self.token = None
        self.server_id = None
        self.websocket = None
        self.received_messages = []
        
    async def test_real_ssh_connection(self):
        """测试真实SSH连接"""
        try:
            logger.info("开始测试真实SSH连接")
            
            # 1. 登录获取token
            if not await self._login():
                logger.error("登录失败")
                return False
            
            # 2. 获取现有SSH服务器
            if not await self._get_existing_server():
                logger.error("获取SSH服务器失败")
                return False
            
            # 3. 测试WebSocket连接
            if not await self._test_websocket_connection():
                logger.error("WebSocket连接测试失败")
                return False
            
            # 4. 测试命令执行
            if not await self._test_commands():
                logger.error("命令执行测试失败")
                return False
            
            logger.info("真实SSH连接测试成功！")
            return True
            
        except Exception as e:
            logger.error(f"测试过程中发生错误: {e}")
            return False
        finally:
            await self._cleanup()
    
    async def _login(self):
        """登录获取JWT token"""
        try:
            login_data = {
                "username": "admin",
                "password": "admin123"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/users/login/",
                json=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access')
                logger.info("登录成功")
                return True
            else:
                logger.error(f"登录失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"登录异常: {e}")
            return False
    
    async def _get_existing_server(self):
        """获取现有SSH服务器"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            response = requests.get(
                f"{self.base_url}/api/v1/resources/servers/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                servers = data.get('results', [])
                
                if servers:
                    # 使用第一个服务器进行测试
                    self.server_id = servers[0]['id']
                    server_info = servers[0]
                    logger.info(f"使用服务器进行测试: {server_info['name']} ({server_info['ip_address']}:{server_info['port']})")
                    return True
                else:
                    logger.error("没有找到可用的SSH服务器")
                    return False
            else:
                logger.error(f"获取服务器列表失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"获取服务器异常: {e}")
            return False
    
    async def _test_websocket_connection(self):
        """测试WebSocket连接"""
        try:
            logger.info("连接WebSocket终端...")
            
            ws_url = f"{self.ws_url}/ws/terminal/{self.server_id}/?token={self.token}"
            
            self.websocket = await websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=10
            )
            
            logger.info("WebSocket连接成功")
            
            # 启动消息接收任务
            asyncio.create_task(self._receive_messages())
            
            # 等待连接建立和初始消息
            await asyncio.sleep(5)
            
            logger.info(f"收到初始消息数量: {len(self.received_messages)}")
            
            # 显示最近的消息
            for msg in self.received_messages[-5:]:
                if isinstance(msg, dict):
                    logger.info(f"消息: {msg.get('type', 'unknown')} - {msg.get('data', msg)}")
                else:
                    logger.info(f"消息: {msg}")
            
            return True
                
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            return False
    
    async def _receive_messages(self):
        """接收WebSocket消息"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.received_messages.append(data)
                    
                    # 实时显示重要消息
                    msg_type = data.get('type', 'unknown')
                    if msg_type in ['error', 'ssh_error', 'connection_status']:
                        logger.info(f"收到重要消息: {msg_type} - {data.get('data', data)}")
                        
                except json.JSONDecodeError:
                    self.received_messages.append({"type": "text", "data": message})
                    logger.debug(f"收到文本消息: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket连接已关闭")
        except Exception as e:
            logger.error(f"接收消息异常: {e}")
    
    async def _test_commands(self):
        """测试命令执行"""
        try:
            logger.info("测试命令执行...")
            
            if not self.websocket:
                logger.error("WebSocket未连接")
                return False
            
            # 等待SSH连接建立
            await asyncio.sleep(3)
            
            # 测试简单命令
            test_commands = [
                "whoami",
                "pwd",
                "echo 'Hello WebSocket Terminal!'",
                "date"
            ]
            
            for command in test_commands:
                logger.info(f"执行命令: {command}")
                
                initial_count = len(self.received_messages)
                
                # 发送命令
                command_message = {
                    "type": "command",
                    "data": command
                }
                
                await self.websocket.send(json.dumps(command_message))
                
                # 等待响应
                await asyncio.sleep(3)
                
                # 检查新消息
                new_messages = self.received_messages[initial_count:]
                if new_messages:
                    logger.info(f"命令 '{command}' 收到 {len(new_messages)} 条响应")
                    for msg in new_messages[-2:]:
                        if isinstance(msg, dict):
                            logger.info(f"  响应: {msg.get('data', msg)}")
                        else:
                            logger.info(f"  响应: {msg}")
                else:
                    logger.warning(f"命令 '{command}' 未收到响应")
                
                # 命令间隔
                await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"命令执行测试异常: {e}")
            return False
    
    async def _cleanup(self):
        """清理资源"""
        try:
            if self.websocket:
                await self.websocket.close()
                logger.info("WebSocket连接已关闭")
        except Exception as e:
            logger.error(f"清理资源异常: {e}")

async def main():
    """主函数"""
    print("=" * 60)
    print("简化WebSocket终端测试 - 真实SSH连接")
    print("=" * 60)
    
    tester = SimpleWebSocketTester()
    
    try:
        success = await tester.test_real_ssh_connection()
        
        print("\n" + "=" * 60)
        if success:
            print("✅ 真实SSH连接测试成功！")
        else:
            print("❌ 真实SSH连接测试失败！")
        print("=" * 60)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n测试过程中发生未预期的错误: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)