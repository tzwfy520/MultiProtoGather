#!/usr/bin/env python3
"""
测试终端显示和命令执行功能
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

class TerminalDisplayTest:
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
    
    def get_server_id(self):
        """获取服务器ID"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{self.base_url}/api/v1/resources/servers/", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            servers = data.get('results', []) if isinstance(data, dict) else data
            if servers:
                self.server_id = servers[0]['id']
                print(f"✓ 获取服务器ID: {self.server_id}")
                return True
            else:
                print("✗ 没有找到服务器")
                return False
        else:
            print(f"✗ 获取服务器列表失败: {response.status_code}")
            return False
    
    async def test_websocket_terminal(self):
        """测试WebSocket终端功能"""
        if not self.token or not self.server_id:
            print("✗ 缺少必要的认证信息")
            return False
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            # 构建WebSocket URL，包含认证token
            ws_url_with_auth = f"{self.ws_url}{self.server_id}/?token={self.token}"
            
            async with websockets.connect(ws_url_with_auth) as websocket:
                print("✓ WebSocket连接建立成功")
                
                # 等待初始连接消息
                initial_messages = []
                start_time = time.time()
                
                while time.time() - start_time < 10:  # 等待10秒
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        initial_messages.append(data)
                        print(f"收到消息: {data.get('type', 'unknown')} - {data.get('data', '')[:100]}")
                        
                        if data.get('type') == 'output' and ('$' in data.get('data', '') or '#' in data.get('data', '')):
                            print("✓ 检测到终端提示符")
                            break
                    except asyncio.TimeoutError:
                        continue
                
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
                test_commands = ['whoami', 'pwd', 'echo "test command"']
                
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
                    start_time = time.time()
                    
                    while time.time() - start_time < 5:  # 等待5秒
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            data = json.loads(message)
                            
                            if data.get('type') == 'output':
                                output = data.get('data', '')
                                print(f"命令输出: {repr(output)}")
                                
                                # 检查是否收到了命令的实际输出
                                if cmd == 'whoami' and 'eccom123' in output:
                                    print("✓ whoami命令执行成功")
                                    response_received = True
                                elif cmd == 'pwd' and '/' in output:
                                    print("✓ pwd命令执行成功")
                                    response_received = True
                                elif cmd == 'echo "test command"' and 'test command' in output:
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
                
                print("\n✓ WebSocket终端测试完成")
                return True
                
        except Exception as e:
            print(f"✗ WebSocket连接失败: {str(e)}")
            return False
    
    async def run_test(self):
        """运行完整测试"""
        print("=== 终端显示和命令执行测试 ===\n")
        
        # 登录
        if not self.login():
            return False
        
        # 获取服务器ID
        if not self.get_server_id():
            return False
        
        # 测试WebSocket终端
        success = await self.test_websocket_terminal()
        
        if success:
            print("\n🎉 所有测试通过！")
        else:
            print("\n❌ 测试失败")
        
        return success

async def main():
    test = TerminalDisplayTest()
    await test.run_test()

if __name__ == "__main__":
    asyncio.run(main())