#!/usr/bin/env python3
"""
WebSocket终端连接测试脚本
用于测试服务器资源管理中的终端登录功能
"""

import asyncio
import websockets
import json
import requests
import sys
import os
import time
import random

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# API配置
API_BASE_URL = 'http://localhost:8000/api/v1'
WS_BASE_URL = 'ws://localhost:8000'

class WebSocketTerminalTester:
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
                print(f"✅ 登录成功，获取到访问令牌")
                return True
            else:
                print(f"❌ 登录失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 登录异常: {str(e)}")
            return False
    
    def get_servers(self):
        """获取服务器列表"""
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = requests.get(f'{API_BASE_URL}/resources/servers/', headers=headers)
            
            if response.status_code == 200:
                servers = response.json()
                print(f"✅ 获取到 {len(servers)} 个服务器")
                
                if servers:
                    self.server_id = servers[0]['id']
                    print(f"📋 使用服务器: {servers[0]['name']} (ID: {self.server_id})")
                    return True
                else:
                    print("⚠️  没有可用的服务器")
                    return False
            else:
                print(f"❌ 获取服务器列表失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 获取服务器列表异常: {str(e)}")
            return False
    
    def create_test_server(self):
        """创建测试服务器"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            server_data = {
                'name': f'测试服务器-{int(time.time())}',
                'ip_address': f'192.168.1.{random.randint(100, 200)}',
                'port': random.randint(2222, 2299),
                'username': 'testuser',
                'password': 'testpass',
                'protocol': 'ssh',
                'description': 'WebSocket测试用服务器'
            }
            
            response = requests.post(
                f'{API_BASE_URL}/resources/servers/', 
                json=server_data, 
                headers=headers
            )
            
            if response.status_code == 201:
                server = response.json()
                self.server_id = server['id']
                print(f"✅ 创建测试服务器成功 (ID: {self.server_id})")
                return True
            else:
                print(f"❌ 创建测试服务器失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 创建测试服务器异常: {str(e)}")
            return False
    
    async def test_websocket_connection(self):
        """测试WebSocket连接"""
        if not self.server_id:
            print("❌ 没有可用的服务器ID")
            return False
        
        ws_url = f'{WS_BASE_URL}/ws/terminal/{self.server_id}/'
        print(f"🔗 尝试连接WebSocket: {ws_url}")
        
        try:
            # 添加认证头（如果需要）
            headers = {}
            if self.access_token:
                headers['Authorization'] = f'Bearer {self.access_token}'
            
            async with websockets.connect(ws_url, extra_headers=headers) as websocket:
                print("✅ WebSocket连接成功建立")
                
                # 监听消息
                async def listen_messages():
                    try:
                        async for message in websocket:
                            data = json.loads(message)
                            msg_type = data.get('type', 'unknown')
                            msg_data = data.get('data', '')
                            
                            print(f"📨 收到消息 [{msg_type}]: {msg_data}")
                            
                            # 如果收到错误消息，返回
                            if msg_type == 'error':
                                return False
                            
                            # 如果终端就绪，发送测试命令
                            if '终端已就绪' in msg_data:
                                print("🚀 发送测试命令: whoami")
                                await websocket.send(json.dumps({
                                    'command': 'whoami'
                                }))
                                
                                # 等待一段时间后关闭连接
                                await asyncio.sleep(3)
                                return True
                                
                    except websockets.exceptions.ConnectionClosed:
                        print("🔌 WebSocket连接已关闭")
                        return False
                    except Exception as e:
                        print(f"❌ 监听消息异常: {str(e)}")
                        return False
                
                # 启动消息监听
                result = await asyncio.wait_for(listen_messages(), timeout=30)
                return result
                
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"❌ WebSocket连接失败 - 状态码错误: {e.status_code}")
            if e.status_code == 404:
                print("💡 提示: WebSocket路由可能未正确配置")
            elif e.status_code == 401:
                print("💡 提示: 可能需要身份认证")
            return False
            
        except websockets.exceptions.ConnectionRefused:
            print("❌ WebSocket连接被拒绝 - 服务器可能未启动")
            return False
            
        except asyncio.TimeoutError:
            print("❌ WebSocket连接超时")
            return False
            
        except Exception as e:
            print(f"❌ WebSocket连接异常: {str(e)}")
            return False
    
    async def run_test(self):
        """运行完整测试"""
        print("🧪 开始WebSocket终端连接测试")
        print("=" * 50)
        
        # 1. 登录
        print("\n1️⃣ 测试用户登录...")
        if not self.login():
            return False
        
        # 2. 获取或创建服务器
        print("\n2️⃣ 获取服务器列表...")
        if not self.get_servers():
            print("\n🔧 尝试创建测试服务器...")
            if not self.create_test_server():
                return False
        
        # 3. 测试WebSocket连接
        print("\n3️⃣ 测试WebSocket终端连接...")
        result = await self.test_websocket_connection()
        
        print("\n" + "=" * 50)
        if result:
            print("🎉 WebSocket终端连接测试通过！")
        else:
            print("💥 WebSocket终端连接测试失败！")
        
        return result

async def main():
    """主函数"""
    tester = WebSocketTerminalTester()
    success = await tester.run_test()
    
    if success:
        print("\n✅ 所有测试通过，WebSocket终端功能正常")
        sys.exit(0)
    else:
        print("\n❌ 测试失败，请检查配置和日志")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())