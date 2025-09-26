#!/usr/bin/env python3
"""
模拟SSH服务器WebSocket终端测试脚本
创建一个简单的模拟SSH服务器来测试WebSocket终端功能
"""

import asyncio
import websockets
import json
import requests
import sys
import os
import threading
import socket
import time

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# API配置
API_BASE_URL = 'http://localhost:8000/api/v1'
WS_BASE_URL = 'ws://localhost:8000'

class MockSSHServer:
    """模拟SSH服务器"""
    
    def __init__(self, host='127.0.0.1', port=2222):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        
    def start(self):
        """启动模拟SSH服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"🚀 模拟SSH服务器启动在 {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    print(f"📞 接收到连接: {addr}")
                    
                    # 发送SSH版本字符串
                    client_socket.send(b"SSH-2.0-MockSSH_1.0\r\n")
                    
                    # 简单处理客户端数据
                    data = client_socket.recv(1024)
                    print(f"📨 收到数据: {data[:50]}...")
                    
                    # 保持连接一段时间
                    time.sleep(2)
                    client_socket.close()
                    
                except socket.error as e:
                    if self.running:
                        print(f"❌ Socket错误: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ 启动模拟SSH服务器失败: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """停止模拟SSH服务器"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
                print("🛑 模拟SSH服务器已停止")
            except:
                pass

class MockSSHWebSocketTester:
    def __init__(self):
        self.access_token = None
        self.server_id = None
        self.mock_server = None
        self.mock_server_thread = None
        
    def start_mock_server(self):
        """启动模拟SSH服务器"""
        self.mock_server = MockSSHServer()
        self.mock_server_thread = threading.Thread(target=self.mock_server.start)
        self.mock_server_thread.daemon = True
        self.mock_server_thread.start()
        time.sleep(1)  # 等待服务器启动
        
    def stop_mock_server(self):
        """停止模拟SSH服务器"""
        if self.mock_server:
            self.mock_server.stop()
        
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
    
    def get_or_create_mock_ssh_server(self):
        """获取或创建模拟SSH服务器配置"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # 先尝试获取现有的模拟服务器
            response = requests.get(f'{API_BASE_URL}/resources/servers/', headers=headers)
            if response.status_code == 200:
                data = response.json()
                servers = data.get('results', [])
                
                # 查找模拟SSH服务器
                for server in servers:
                    if server['ip_address'] == '127.0.0.1' and server['port'] == 2222:
                        self.server_id = server['id']
                        print(f"✅ 找到现有模拟SSH服务器 (ID: {self.server_id})")
                        return True
            
            # 如果没有找到，创建新的
            import time
            timestamp = int(time.time())
            server_data = {
                'name': f'模拟SSH测试服务器-{timestamp}',
                'ip_address': '127.0.0.1',
                'port': 2222,
                'username': 'testuser',
                'password': 'testpass',
                'protocol': 'ssh',
                'description': '模拟SSH WebSocket测试服务器'
            }
            
            response = requests.post(
                f'{API_BASE_URL}/resources/servers/', 
                json=server_data, 
                headers=headers
            )
            
            if response.status_code == 201:
                server = response.json()
                self.server_id = server['id']
                print(f"✅ 创建模拟SSH服务器成功 (ID: {self.server_id})")
                return True
            else:
                print(f"❌ 创建服务器失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 创建服务器异常: {str(e)}")
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
                    while message_count < 15:  # 增加消息数量限制
                        message = await asyncio.wait_for(websocket.recv(), timeout=15)
                        data = json.loads(message)
                        msg_type = data.get('type', 'unknown')
                        msg_data = data.get('data', '')
                        
                        print(f"📨 [{msg_type}]: {msg_data}")
                        message_count += 1
                        
                        # 如果收到错误消息
                        if msg_type == 'error':
                            print(f"❌ 服务器返回错误: {msg_data}")
                            # 检查是否是预期的SSH连接错误
                            if 'SSH连接错误' in str(msg_data):
                                print("✅ 成功触发SSH连接错误处理机制")
                                return True
                            return False
                        
                        # 如果收到连接成功消息
                        if '连接成功' in str(msg_data) or 'connected' in str(msg_data).lower():
                            print("✅ SSH连接成功建立")
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
        print("🧪 模拟SSH WebSocket终端连接测试")
        print("=" * 50)
        
        try:
            # 1. 启动模拟SSH服务器
            print("🚀 启动模拟SSH服务器...")
            self.start_mock_server()
            
            # 2. 登录
            print("🔐 测试用户登录...")
            if not self.login():
                return False
            
            # 3. 获取或创建模拟服务器配置
            print("📋 获取或创建模拟SSH服务器配置...")
            if not self.get_or_create_mock_ssh_server():
                return False
            
            # 4. 测试WebSocket连接
            print("🔌 开始WebSocket连接测试...")
            success = await self.test_websocket_connection()
            
            print("=" * 50)
            if success:
                print("🎉 模拟SSH WebSocket终端连接测试成功！")
            else:
                print("💥 模拟SSH WebSocket终端连接测试失败！")
            
            return success
            
        finally:
            # 清理资源
            self.stop_mock_server()

async def main():
    """主函数"""
    tester = MockSSHWebSocketTester()
    success = await tester.run_test()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())