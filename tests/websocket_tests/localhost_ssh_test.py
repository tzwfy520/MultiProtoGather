#!/usr/bin/env python3
"""
本地SSH连接测试脚本
测试连接到本地SSH服务器
"""

import asyncio
import websockets
import json
import requests
import time
import logging
import subprocess
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LocalSSHTester:
    """本地SSH连接测试器"""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.ws_url = "ws://127.0.0.1:8000"
        self.token = None
        self.server_id = None
        self.websocket = None
        self.received_messages = []
        
    async def test_localhost_ssh(self):
        """测试本地SSH连接"""
        try:
            logger.info("开始测试本地SSH连接")
            
            # 1. 检查本地SSH服务
            if not self._check_local_ssh():
                logger.error("本地SSH服务不可用")
                return False
            
            # 2. 登录获取token
            if not await self._login():
                logger.error("登录失败")
                return False
            
            # 3. 创建或获取本地SSH服务器配置
            if not await self._setup_localhost_server():
                logger.error("设置本地SSH服务器失败")
                return False
            
            # 4. 测试WebSocket连接
            if not await self._test_websocket_connection():
                logger.error("WebSocket连接测试失败")
                return False
            
            # 5. 测试命令执行
            if not await self._test_commands():
                logger.error("命令执行测试失败")
                return False
            
            logger.info("本地SSH连接测试成功！")
            return True
            
        except Exception as e:
            logger.error(f"测试过程中发生错误: {e}")
            return False
        finally:
            await self._cleanup()
    
    def _check_local_ssh(self):
        """检查本地SSH服务是否可用"""
        try:
            # 检查SSH服务是否运行
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", 
                 f"{os.getenv('USER')}@localhost", "echo", "test"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("本地SSH服务可用")
                return True
            else:
                logger.warning(f"本地SSH连接测试失败: {result.stderr}")
                
                # 尝试启动SSH服务（macOS）
                logger.info("尝试启用远程登录...")
                try:
                    subprocess.run(["sudo", "systemsetup", "-setremotelogin", "on"], 
                                 capture_output=True, timeout=10)
                    time.sleep(2)
                    
                    # 再次测试
                    result = subprocess.run(
                        ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", 
                         f"{os.getenv('USER')}@localhost", "echo", "test"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        logger.info("SSH服务启用成功")
                        return True
                        
                except Exception as e:
                    logger.warning(f"启用SSH服务失败: {e}")
                
                return False
                
        except Exception as e:
            logger.error(f"检查SSH服务异常: {e}")
            return False
    
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
    
    async def _setup_localhost_server(self):
        """设置本地SSH服务器配置"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # 首先检查是否已有本地服务器配置
            response = requests.get(
                f"{self.base_url}/api/v1/resources/servers/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                servers = data.get('results', [])
                
                # 查找本地服务器
                localhost_server = None
                for server in servers:
                    if server['ip_address'] in ['127.0.0.1', 'localhost'] and server['port'] == 22:
                        localhost_server = server
                        break
                
                if localhost_server:
                    self.server_id = localhost_server['id']
                    logger.info(f"使用现有本地服务器: {localhost_server['name']}")
                    return True
                else:
                    # 创建新的本地服务器配置
                    return await self._create_localhost_server(headers)
            else:
                logger.error(f"获取服务器列表失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"设置本地服务器异常: {e}")
            return False
    
    async def _create_localhost_server(self, headers):
        """创建本地SSH服务器配置"""
        try:
            current_user = os.getenv('USER')
            
            server_data = {
                "name": f"本地SSH服务器-{current_user}",
                "ip_address": "127.0.0.1",
                "port": 22,
                "username": current_user,
                "password": "",  # 使用密钥认证
                "private_key": "",  # 可以为空，系统会尝试默认密钥
                "os_type": "linux",
                "description": "本地SSH服务器测试"
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
                logger.info(f"创建本地服务器成功: {server['name']}")
                return True
            else:
                logger.error(f"创建本地服务器失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"创建本地服务器异常: {e}")
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
            await asyncio.sleep(8)  # 给SSH连接更多时间
            
            logger.info(f"收到初始消息数量: {len(self.received_messages)}")
            
            # 显示最近的消息
            for msg in self.received_messages[-10:]:
                if isinstance(msg, dict):
                    msg_type = msg.get('type', 'unknown')
                    msg_data = msg.get('data', msg)
                    logger.info(f"消息: {msg_type} - {msg_data}")
                else:
                    logger.info(f"消息: {msg}")
            
            # 检查是否有SSH连接错误
            error_messages = [msg for msg in self.received_messages 
                            if isinstance(msg, dict) and msg.get('type') == 'error']
            
            if error_messages:
                logger.warning("发现错误消息:")
                for error in error_messages:
                    logger.warning(f"  错误: {error.get('data', error)}")
            
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
                    if msg_type in ['error', 'ssh_error', 'connection_status', 'output']:
                        logger.debug(f"收到消息: {msg_type} - {data.get('data', data)}")
                        
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
            
            # 等待SSH连接完全建立
            await asyncio.sleep(5)
            
            # 检查是否有终端就绪的消息
            ready_messages = [msg for msg in self.received_messages 
                            if isinstance(msg, dict) and 
                            ('ready' in str(msg.get('data', '')).lower() or 
                             'welcome' in str(msg.get('data', '')).lower() or
                             msg.get('type') == 'output')]
            
            if not ready_messages:
                logger.warning("未检测到终端就绪消息，但继续测试...")
            
            # 测试简单命令
            test_commands = [
                "whoami",
                "pwd",
                "echo 'Hello Local SSH!'",
                "uname -a"
            ]
            
            success_count = 0
            
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
                await asyncio.sleep(4)
                
                # 检查新消息
                new_messages = self.received_messages[initial_count:]
                if new_messages:
                    logger.info(f"命令 '{command}' 收到 {len(new_messages)} 条响应")
                    
                    # 查找输出消息
                    output_messages = [msg for msg in new_messages 
                                     if isinstance(msg, dict) and 
                                     msg.get('type') in ['output', 'message'] and
                                     '终端未就绪' not in str(msg.get('data', ''))]
                    
                    if output_messages:
                        success_count += 1
                        for msg in output_messages[-2:]:
                            logger.info(f"  输出: {msg.get('data', msg)}")
                    else:
                        logger.warning(f"命令 '{command}' 未收到有效输出")
                        for msg in new_messages[-2:]:
                            if isinstance(msg, dict):
                                logger.warning(f"  响应: {msg.get('data', msg)}")
                else:
                    logger.warning(f"命令 '{command}' 未收到响应")
                
                # 命令间隔
                await asyncio.sleep(2)
            
            logger.info(f"成功执行命令数: {success_count}/{len(test_commands)}")
            return success_count > 0  # 至少有一个命令成功
            
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
    print("本地SSH连接测试")
    print("=" * 60)
    
    tester = LocalSSHTester()
    
    try:
        success = await tester.test_localhost_ssh()
        
        print("\n" + "=" * 60)
        if success:
            print("✅ 本地SSH连接测试成功！")
        else:
            print("❌ 本地SSH连接测试失败！")
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