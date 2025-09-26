#!/usr/bin/env python3
"""
WebSocket终端输入测试脚本
用于测试终端输入功能的WebSocket消息传递
"""

import asyncio
import websockets
import json
import sys
import time

class TerminalInputTester:
    def __init__(self, server_id, token):
        self.server_id = server_id
        self.token = token
        self.websocket = None
        self.connected = False
        
    async def connect(self):
        """连接到WebSocket服务器"""
        try:
            uri = f"ws://localhost:8000/ws/terminal/{self.server_id}/?token={self.token}"
            print(f"🔗 连接到: {uri}")
            
            self.websocket = await websockets.connect(uri)
            self.connected = True
            print("✅ WebSocket连接成功")
            
            # 启动消息监听
            asyncio.create_task(self.listen_messages())
            
        except Exception as e:
            print(f"❌ WebSocket连接失败: {e}")
            return False
        
        return True
    
    async def listen_messages(self):
        """监听WebSocket消息"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type', 'unknown')
                    content = data.get('data', '')
                    
                    print(f"📥 收到消息: type={msg_type}, data={repr(content)}")
                    
                    if msg_type == 'output':
                        print(f"📺 终端输出: {content}")
                    elif msg_type == 'error':
                        print(f"❌ 错误消息: {content}")
                    elif msg_type == 'message':
                        print(f"💬 系统消息: {content}")
                        
                except json.JSONDecodeError:
                    print(f"📥 收到非JSON消息: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("🔌 WebSocket连接已关闭")
            self.connected = False
        except Exception as e:
            print(f"❌ 消息监听错误: {e}")
    
    async def send_input(self, input_data):
        """发送输入数据"""
        if not self.connected or not self.websocket:
            print("❌ WebSocket未连接")
            return False
        
        try:
            message = json.dumps({
                'type': 'input',
                'data': input_data
            })
            
            print(f"📤 发送输入: {repr(input_data)}")
            await self.websocket.send(message)
            return True
            
        except Exception as e:
            print(f"❌ 发送输入失败: {e}")
            return False
    
    async def test_basic_commands(self):
        """测试基本命令"""
        print("\n🧪 开始基本命令测试...")
        
        # 等待连接稳定
        await asyncio.sleep(2)
        
        # 测试简单命令
        test_commands = [
            "echo 'Hello World'",
            "pwd",
            "ls -la",
            "whoami",
            "date"
        ]
        
        for cmd in test_commands:
            print(f"\n🔧 测试命令: {cmd}")
            
            # 发送每个字符
            for char in cmd:
                await self.send_input(char)
                await asyncio.sleep(0.1)  # 模拟真实输入速度
            
            # 发送回车
            await self.send_input('\r')
            
            # 等待输出
            await asyncio.sleep(2)
    
    async def test_special_keys(self):
        """测试特殊按键"""
        print("\n🧪 开始特殊按键测试...")
        
        # 测试特殊按键
        special_keys = {
            'Backspace': '\x7f',
            'Tab': '\t',
            'Escape': '\x1b',
            'ArrowUp': '\x1b[A',
            'ArrowDown': '\x1b[B',
            'ArrowLeft': '\x1b[D',
            'ArrowRight': '\x1b[C',
            'Home': '\x1b[H',
            'End': '\x1b[F'
        }
        
        for key_name, key_sequence in special_keys.items():
            print(f"\n🔧 测试特殊键: {key_name}")
            await self.send_input(key_sequence)
            await asyncio.sleep(1)
    
    async def test_ctrl_combinations(self):
        """测试Ctrl组合键"""
        print("\n🧪 开始Ctrl组合键测试...")
        
        ctrl_keys = {
            'Ctrl+C': '\x03',
            'Ctrl+D': '\x04',
            'Ctrl+L': '\x0c',
            'Ctrl+Z': '\x1a'
        }
        
        for key_name, key_sequence in ctrl_keys.items():
            print(f"\n🔧 测试组合键: {key_name}")
            await self.send_input(key_sequence)
            await asyncio.sleep(1)
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 WebSocket连接已断开")

async def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("使用方法: python test_terminal_input.py <server_id> <token>")
        print("示例: python test_terminal_input.py 1 your_jwt_token")
        return
    
    server_id = sys.argv[1]
    token = sys.argv[2]
    
    print("🚀 启动WebSocket终端输入测试")
    print(f"📋 服务器ID: {server_id}")
    print(f"🔑 Token: {token[:20]}...")
    
    tester = TerminalInputTester(server_id, token)
    
    try:
        # 连接WebSocket
        if not await tester.connect():
            return
        
        # 等待连接稳定
        print("⏳ 等待连接稳定...")
        await asyncio.sleep(3)
        
        # 运行测试
        await tester.test_basic_commands()
        await tester.test_special_keys()
        await tester.test_ctrl_combinations()
        
        print("\n✅ 所有测试完成")
        
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
    finally:
        await tester.disconnect()

if __name__ == "__main__":
    asyncio.run(main())