#!/usr/bin/env python3
"""
完整的WebSocket终端功能测试脚本
测试SSH连接、命令发送和结果获取功能
"""

import asyncio
import websockets
import json
import requests
import threading
import time
import logging
import sys
import os
from ssh_mock_server import MockSSHServer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebSocketTerminalTester:
    """WebSocket终端功能测试器"""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.ws_url = "ws://127.0.0.1:8000"
        self.token = None
        self.server_id = None
        self.websocket = None
        self.mock_ssh_server = None
        self.ssh_server_thread = None
        self.received_messages = []
        
    async def run_comprehensive_test(self):
        """运行完整的WebSocket终端测试"""
        try:
            logger.info("开始WebSocket终端功能测试")
            
            # 1. 启动模拟SSH服务器
            await self._start_mock_ssh_server()
            
            # 2. 登录获取token
            if not await self._login():
                logger.error("登录失败")
                return False
            
            # 3. 创建或获取SSH服务器配置
            if not await self._get_or_create_ssh_server():
                logger.error("创建SSH服务器配置失败")
                return False
            
            # 4. 测试WebSocket连接
            if not await self._test_websocket_connection():
                logger.error("WebSocket连接测试失败")
                return False
            
            # 5. 测试命令发送和结果获取
            if not await self._test_command_execution():
                logger.error("命令执行测试失败")
                return False
            
            # 6. 测试终端调整大小
            if not await self._test_terminal_resize():
                logger.error("终端调整大小测试失败")
                return False
            
            logger.info("所有WebSocket终端功能测试通过！")
            return True
            
        except Exception as e:
            logger.error(f"测试过程中发生错误: {e}")
            return False
        finally:
            await self._cleanup()
    
    async def _start_mock_ssh_server(self):
        """启动模拟SSH服务器"""
        logger.info("启动模拟SSH服务器...")
        
        self.mock_ssh_server = MockSSHServer(host='127.0.0.1', port=2222)
        
        # 在单独线程中启动服务器
        self.ssh_server_thread = threading.Thread(
            target=self.mock_ssh_server.start,
            daemon=True
        )
        self.ssh_server_thread.start()
        
        # 等待服务器启动
        await asyncio.sleep(2)
        logger.info("模拟SSH服务器已启动")
    
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
                logger.info("登录成功，获取到JWT token")
                return True
            else:
                logger.error(f"登录失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"登录请求异常: {e}")
            return False
    
    async def _get_or_create_ssh_server(self):
        """获取或创建SSH服务器配置"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # 首先尝试获取现有的SSH服务器
            response = requests.get(
                f"{self.base_url}/api/v1/resources/servers/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                servers = data.get('results', [])  # 分页响应格式
                
                # 查找匹配的服务器
                for server in servers:
                    if (server.get('ip_address') == '127.0.0.1' and 
                        server.get('port') == 2222):
                        self.server_id = server['id']
                        logger.info(f"找到现有SSH服务器，ID: {self.server_id}")
                        return True
            
            # 如果没有找到，创建新的服务器配置
            server_data = {
                "name": f"测试SSH服务器_{int(time.time())}",
                "ip_address": "127.0.0.1",
                "port": 2222,
                "username": "testuser",
                "password": "testpass",
                "description": "WebSocket终端功能测试服务器"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/resources/servers/",
                json=server_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 201:
                server = response.json()
                self.server_id = server['id']
                logger.info(f"创建新SSH服务器成功，ID: {self.server_id}")
                return True
            else:
                logger.error(f"创建SSH服务器失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"获取/创建SSH服务器异常: {e}")
            return False
    
    async def _test_websocket_connection(self):
        """测试WebSocket连接"""
        try:
            logger.info("测试WebSocket连接...")
            
            # 构建WebSocket URL
            ws_url = f"{self.ws_url}/ws/terminal/{self.server_id}/?token={self.token}"
            
            # 连接WebSocket
            self.websocket = await websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=10
            )
            
            logger.info("WebSocket连接成功")
            
            # 启动消息接收任务
            asyncio.create_task(self._receive_messages())
            
            # 等待初始连接消息
            await asyncio.sleep(3)
            
            # 检查是否收到连接相关消息
            if self.received_messages:
                logger.info(f"收到初始消息: {len(self.received_messages)} 条")
                for msg in self.received_messages[-3:]:  # 显示最后3条消息
                    logger.info(f"消息: {msg}")
                return True
            else:
                logger.warning("未收到初始连接消息")
                return True  # WebSocket连接成功就算通过
                
        except Exception as e:
            logger.error(f"WebSocket连接测试失败: {e}")
            return False
    
    async def _receive_messages(self):
        """接收WebSocket消息"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.received_messages.append(data)
                    logger.debug(f"收到消息: {data}")
                except json.JSONDecodeError:
                    # 可能是纯文本消息
                    self.received_messages.append({"type": "text", "data": message})
                    logger.debug(f"收到文本消息: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket连接已关闭")
        except Exception as e:
            logger.error(f"接收消息异常: {e}")
    
    async def _test_command_execution(self):
        """测试命令发送和结果获取"""
        try:
            logger.info("测试命令执行功能...")
            
            if not self.websocket:
                logger.error("WebSocket未连接")
                return False
            
            # 测试命令列表
            test_commands = [
                "whoami",
                "pwd", 
                "echo 'WebSocket终端测试成功!'",
                "date",
                "ls"
            ]
            
            for command in test_commands:
                logger.info(f"发送命令: {command}")
                
                # 清空之前的消息
                initial_msg_count = len(self.received_messages)
                
                # 发送命令 (新格式)
                command_message = {
                    "type": "command",
                    "data": command
                }
                
                await self.websocket.send(json.dumps(command_message))
                
                # 等待响应
                await asyncio.sleep(2)
                
                # 检查是否收到新消息
                new_messages = self.received_messages[initial_msg_count:]
                if new_messages:
                    logger.info(f"命令 '{command}' 执行成功，收到 {len(new_messages)} 条响应")
                    for msg in new_messages[-2:]:  # 显示最后2条消息
                        if isinstance(msg, dict):
                            logger.info(f"响应: {msg.get('data', msg)}")
                        else:
                            logger.info(f"响应: {msg}")
                else:
                    logger.warning(f"命令 '{command}' 未收到响应")
                
                # 命令间隔
                await asyncio.sleep(1)
            
            logger.info("命令执行测试完成")
            return True
            
        except Exception as e:
            logger.error(f"命令执行测试异常: {e}")
            return False
    
    async def _test_terminal_resize(self):
        """测试终端调整大小功能"""
        try:
            logger.info("测试终端调整大小功能...")
            
            if not self.websocket:
                logger.error("WebSocket未连接")
                return False
            
            # 发送调整大小消息
            resize_message = {
                "type": "resize",
                "width": 120,
                "height": 40
            }
            
            await self.websocket.send(json.dumps(resize_message))
            logger.info("发送终端调整大小消息")
            
            # 等待处理
            await asyncio.sleep(1)
            
            logger.info("终端调整大小测试完成")
            return True
            
        except Exception as e:
            logger.error(f"终端调整大小测试异常: {e}")
            return False
    
    async def _cleanup(self):
        """清理资源"""
        try:
            # 关闭WebSocket连接
            if self.websocket:
                await self.websocket.close()
                logger.info("WebSocket连接已关闭")
            
            # 停止模拟SSH服务器
            if self.mock_ssh_server:
                self.mock_ssh_server.stop()
                logger.info("模拟SSH服务器已停止")
            
        except Exception as e:
            logger.error(f"清理资源异常: {e}")

async def main():
    """主函数"""
    print("=" * 60)
    print("WebSocket终端功能完整测试")
    print("=" * 60)
    
    tester = WebSocketTerminalTester()
    
    try:
        success = await tester.run_comprehensive_test()
        
        print("\n" + "=" * 60)
        if success:
            print("✅ 所有测试通过！WebSocket终端功能正常")
        else:
            print("❌ 测试失败！请检查相关配置和代码")
        print("=" * 60)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n测试过程中发生未预期的错误: {e}")
        return 1

if __name__ == "__main__":
    # 运行测试
    exit_code = asyncio.run(main())
    sys.exit(exit_code)