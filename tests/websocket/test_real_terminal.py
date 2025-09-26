#!/usr/bin/env python3
"""
使用真实服务器测试终端显示和命令执行功能
"""
import asyncio
import websockets
import json
import requests
import time
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class RealTerminalTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000/ws/terminal/"
        self.token = None
        self.server_id = None
        
    def login(self):
        """登录获取token"""
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = requests.post(f"{self.base_url}/api/v1/users/login/", json=login_data)
        if response.status_code == 200:
            data = response.json()
            self.token = data.get('access')
            print(f"✓ 登录成功，获取token: {self.token[:20]}...")
            return True
        else:
            print(f"✗ 登录失败: {response.status_code} - {response.text}")
            return False
    
    def create_real_server(self):
        """创建真实服务器配置"""
        server_data = {
            "name": "真实SSH测试服务器",
            "ip_address": "127.0.0.1",  # 本地测试
            "port": 22,  # 标准SSH端口
            "username": "eccom123",  # 使用实际用户名
            "password": "your_password_here",  # 需要替换为实际密码
            "os_type": "linux",
            "description": "用于测试终端功能的真实服务器"
        }
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(f"{self.base_url}/api/v1/resources/servers/", 
                               json=server_data, headers=headers)
        
        if response.status_code == 201:
            server = response.json()
            self.server_id = server['id']
            print(f"✓ 创建服务器成功，ID: {self.server_id}")
            return True
        else:
            print(f"✗ 创建服务器失败: {response.status_code} - {response.text}")
            return False
    
    def get_existing_server(self):
        """获取现有服务器"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{self.base_url}/api/v1/resources/servers/", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            servers = data.get('results', []) if isinstance(data, dict) else data
            
            # 查找真实服务器（非127.0.0.1:2222的模拟服务器）
            for server in servers:
                if server.get('port') != 2222:  # 排除模拟服务器
                    self.server_id = server['id']
                    print(f"✓ 使用现有服务器，ID: {self.server_id}, 名称: {server.get('name')}")
                    return True
            
            print("✗ 没有找到合适的真实服务器")
            return False
        else:
            print(f"✗ 获取服务器列表失败: {response.status_code}")
            return False
    
    async def test_websocket_terminal(self):
        """测试WebSocket终端功能"""
        if not self.token or not self.server_id:
            print("✗ 缺少必要的认证信息")
            return False
        
        try:
            # 构建WebSocket URL，包含认证token
            ws_url_with_auth = f"{self.ws_url}{self.server_id}/?token={self.token}"
            
            async with websockets.connect(ws_url_with_auth) as websocket:
                print("✓ WebSocket连接建立成功")
                
                # 等待初始连接消息
                initial_messages = []
                start_time = time.time()
                terminal_ready = False
                
                print("等待SSH连接建立...")
                while time.time() - start_time < 15:  # 等待15秒
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(message)
                        initial_messages.append(data)
                        
                        msg_type = data.get('type', 'unknown')
                        msg_data = data.get('data', '')
                        
                        print(f"收到消息: {msg_type} - {msg_data[:100]}")
                        
                        if msg_type == 'error':
                            print(f"✗ 连接错误: {msg_data}")
                            return False
                        
                        if msg_type == 'output' and ('$' in msg_data or '#' in msg_data):
                            print("✓ 检测到终端提示符，连接成功")
                            terminal_ready = True
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                if not terminal_ready:
                    print("✗ 终端未就绪，连接可能失败")
                    return False
                
                # 检查初始输出中的用户名显示
                print("\n=== 检查用户名显示 ===")
                for msg in initial_messages:
                    if msg.get('type') == 'output':
                        output = msg.get('data', '')
                        if 'eccom123' in output:
                            print(f"用户名输出: {repr(output)}")
                            # 检查是否包含ANSI转义序列
                            if '[?2004h' in output or '\x1b' in output:
                                print("✗ 输出仍包含ANSI转义序列")
                            else:
                                print("✓ ANSI转义序列已清理")
                
                # 测试命令执行
                print("\n=== 测试命令执行 ===")
                test_commands = ['whoami', 'pwd', 'echo "Hello Terminal Test"']
                
                for cmd in test_commands:
                    print(f"\n发送命令: {cmd}")
                    
                    # 发送命令
                    command_msg = {
                        "type": "command",
                        "data": cmd
                    }
                    await websocket.send(json.dumps(command_msg))
                    
                    # 等待响应
                    response_received = False
                    command_output = []
                    start_time = time.time()
                    
                    while time.time() - start_time < 8:  # 等待8秒
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            data = json.loads(message)
                            
                            if data.get('type') == 'output':
                                output = data.get('data', '')
                                command_output.append(output)
                                print(f"命令输出: {repr(output)}")
                                
                                # 检查是否收到了命令的实际输出
                                if cmd == 'whoami' and 'eccom123' in output:
                                    print("✓ whoami命令执行成功")
                                    response_received = True
                                elif cmd == 'pwd' and '/' in output and output.strip() != cmd:
                                    print("✓ pwd命令执行成功")
                                    response_received = True
                                elif cmd == 'echo "Hello Terminal Test"' and 'Hello Terminal Test' in output:
                                    print("✓ echo命令执行成功")
                                    response_received = True
                                elif '$' in output or '#' in output:
                                    print("收到提示符")
                                    if response_received:
                                        break
                        except asyncio.TimeoutError:
                            continue
                    
                    if not response_received:
                        print(f"✗ 命令 {cmd} 未收到预期响应")
                        print(f"所有输出: {command_output}")
                    
                    # 短暂等待，避免命令重叠
                    await asyncio.sleep(1)
                
                print("\n✓ WebSocket终端测试完成")
                return True
                
        except Exception as e:
            print(f"✗ WebSocket连接失败: {str(e)}")
            return False
    
    async def run_test(self):
        """运行完整测试"""
        print("=== 真实服务器终端功能测试 ===\n")
        
        # 登录
        if not self.login():
            return False
        
        # 获取现有服务器或创建新服务器
        if not self.get_existing_server():
            print("尝试创建新的测试服务器...")
            if not self.create_real_server():
                print("✗ 无法获取或创建测试服务器")
                return False
        
        # 测试WebSocket终端
        success = await self.test_websocket_terminal()
        
        if success:
            print("\n🎉 真实服务器测试通过！")
        else:
            print("\n❌ 真实服务器测试失败")
        
        return success

async def main():
    test = RealTerminalTest()
    await test.run_test()

if __name__ == "__main__":
    asyncio.run(main())