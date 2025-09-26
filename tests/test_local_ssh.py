#!/usr/bin/env python3
"""
本地SSH WebSocket终端测试脚本
测试连接到本地SSH服务的WebSocket终端功能
"""

import asyncio
import websockets
import json
import requests
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# API配置
API_BASE_URL = 'http://localhost:8000/api/v1'
WS_BASE_URL = 'ws://localhost:8000'

class LocalSSHWebSocketTester:
    def __init__(self):
        self.access_token = None
        self.server_id = None
        
    def login(self, username='admin', password='admin123'):
        """登录获取访问令牌"""
        try:
            response = requests.post(f'{API_BASE_URL}/users/login/', {
                'username': username,
                'password': password
            })
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access')
                print(f"✅ 登录成功")
                return True
            else:
                print(f"❌ 登录失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 登录异常: {str(e)}")
            return False
    
    def create_local_ssh_server(self):
        """创建本地SSH服务器配置"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # 使用本地SSH服务器配置
            server_data = {
                'name': '本地SSH测试服务器',
                'ip_address': '127.0.0.1',
                'port': 22,
                'username': os.getenv('USER', 'testuser'),  # 使用当前用户名
                'password': '',  # 空密码，依赖系统认证
                'protocol': 'ssh',
                'description': '本地SSH WebSocket测试服务器'
            }
            
            response = requests.post(
                f'{API_BASE_URL}/resources/servers/', 
                json=server_data, 
                headers=headers
            )
            
            if response.status_code == 201:
                server = response.json()
                self.server_id = server['id']
                print(f"✅ 创建本地SSH服务器成功 (ID: {self.server_id})")
                return True
            else:
                print(f"❌ 创建服务器失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 创建服务器异常: {str(e)}")
            return False
    
    def get_existing_server(self):
        """获取现有的本地服务器"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
            }
            
            response = requests.get(f'{API_BASE_URL}/resources/servers/', headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                servers = data.get('results', [])
                
                # 查找本地服务器
                for server in servers:
                    if server['ip_address'] == '127.0.0.1':
                        self.server_id = server['id']
                        print(f"✅ 找到本地服务器 (ID: {self.server_id}): {server['name']}")
                        return True
                
                print("📝 未找到本地服务器，将创建新的")
                return False
                
        except Exception as e:
            print(f"❌ 获取服务器列表异常: {str(e)}")
            return False
    
    async def test_websocket_connection(self):
        """测试WebSocket连接"""
        if not self.server_id:
            print("❌ 没有可用的服务器ID")
            return False
        
        ws_url = f'{WS_BASE_URL}/ws/terminal/{self.server_id}/?token={self.access_token}'
        print(f"🔗 连接WebSocket: ws://localhost:8000/ws/terminal/{self.server_id}/")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print("✅ WebSocket连接成功建立")
                
                # 监听消息
                message_count = 0
                try:
                    while message_count < 10:  # 限制消息数量避免无限循环
                        message = await asyncio.wait_for(websocket.recv(), timeout=20)
                        data = json.loads(message)
                        msg_type = data.get('type', 'unknown')
                        msg_data = data.get('data', '')
                        
                        print(f"📨 [{msg_type}]: {msg_data}")
                        message_count += 1
                        
                        # 如果收到错误消息
                        if msg_type == 'error':
                            print(f"❌ 服务器返回错误: {msg_data}")
                            return False
                        
                        # 如果终端就绪，发送测试命令
                        if '就绪' in str(msg_data) or 'ready' in str(msg_data).lower():
                            print("🎯 终端就绪，发送测试命令...")
                            test_command = {"type": "command", "data": "echo 'WebSocket终端测试成功!'\\n"}
                            await websocket.send(json.dumps(test_command))
                            
                            # 等待命令响应
                            response = await asyncio.wait_for(websocket.recv(), timeout=10)
                            response_data = json.loads(response)
                            print(f"📨 命令响应: {response_data}")
                            
                            print("✅ WebSocket终端连接测试成功！")
                            return True
                
                except asyncio.TimeoutError:
                    print("⏰ WebSocket消息接收超时")
                    return False
                    
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"❌ WebSocket连接被关闭: {e}")
            return False
        except Exception as e:
            print(f"❌ WebSocket连接异常: {e}")
            return False
    
    async def run_test(self):
        """运行完整测试"""
        print("🧪 本地SSH WebSocket终端连接测试")
        print("=" * 50)
        
        # 1. 登录
        print("🔐 测试用户登录...")
        if not self.login():
            return False
        
        # 2. 获取或创建本地服务器
        print("📋 检查本地SSH服务器...")
        if not self.get_existing_server():
            if not self.create_local_ssh_server():
                return False
        
        # 3. 测试WebSocket连接
        print("🔌 开始WebSocket连接测试...")
        success = await self.test_websocket_connection()
        
        print("=" * 50)
        if success:
            print("🎉 本地SSH WebSocket终端连接测试成功！")
        else:
            print("💥 本地SSH WebSocket终端连接测试失败！")
        
        return success

async def main():
    """主函数"""
    tester = LocalSSHWebSocketTester()
    success = await tester.run_test()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())