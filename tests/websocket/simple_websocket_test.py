#!/usr/bin/env python3
"""
简化的WebSocket终端连接测试
"""

import asyncio
import websockets
import json
import requests
import sys

# API配置
API_BASE_URL = 'http://localhost:8000/api/v1'
WS_BASE_URL = 'ws://localhost:8000'

async def test_websocket_direct():
    """直接测试WebSocket连接"""
    print("🔗 直接测试WebSocket连接...")
    
    # 使用现有服务器ID进行测试
    server_id = 1  # 假设存在ID为1的服务器
    ws_url = f'{WS_BASE_URL}/ws/terminal/{server_id}/'
    
    print(f"📡 连接URL: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket连接成功建立")
            
            # 发送测试消息
            test_message = {"command": "echo 'WebSocket测试'"}
            await websocket.send(json.dumps(test_message))
            print(f"📤 发送测试消息: {test_message}")
            
            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                print(f"📨 收到响应: {data}")
                return True
            except asyncio.TimeoutError:
                print("⏰ 等待响应超时")
                return False
                
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket连接失败 - 状态码: {e.status_code}")
        if e.status_code == 404:
            print("💡 提示: WebSocket路由未找到")
        elif e.status_code == 401:
            print("💡 提示: 需要身份认证")
        return False
        
    except websockets.exceptions.ConnectionRefused:
        print("❌ WebSocket连接被拒绝")
        return False
        
    except Exception as e:
        print(f"❌ WebSocket连接异常: {str(e)}")
        return False

def test_login():
    """测试登录"""
    print("🔐 测试用户登录...")
    
    try:
        response = requests.post(f'{API_BASE_URL}/users/login/', {
            'username': 'admin',
            'password': 'admin123'
        })
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access')
            print(f"✅ 登录成功")
            return access_token
        else:
            print(f"❌ 登录失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 登录异常: {str(e)}")
        return None

def get_servers(access_token):
    """获取服务器列表"""
    print("📋 获取服务器列表...")
    
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f'{API_BASE_URL}/resources/servers/', headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            servers = data.get('results', [])  # API返回的是分页格式
            print(f"✅ 获取到 {len(servers)} 个服务器")
            
            if servers:
                for i, server in enumerate(servers):
                    if i < 3:  # 只显示前3个
                        print(f"  {i+1}. {server['name']} (ID: {server['id']}) - {server['ip_address']}:{server['port']}")
                return servers[0]['id']  # 返回第一个服务器ID
            else:
                print("⚠️  没有可用的服务器")
                return None
        else:
            print(f"❌ 获取服务器列表失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 获取服务器列表异常: {str(e)}")
        return None

async def test_websocket_with_auth(server_id, access_token):
    """使用认证测试WebSocket连接"""
    print(f"🔗 测试WebSocket连接 (服务器ID: {server_id})...")
    
    # 在URL中添加token参数
    ws_url = f'{WS_BASE_URL}/ws/terminal/{server_id}/?token={access_token}'
    print(f"📡 连接URL: {ws_url}")
    
    try:
        # WebSocket连接，通过URL参数传递token
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket连接成功建立")
            
            # 监听消息
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=15)
                    data = json.loads(message)
                    msg_type = data.get('type', 'unknown')
                    msg_data = data.get('data', '')
                    
                    print(f"📨 收到消息 [{msg_type}]: {msg_data}")
                    
                    # 如果收到错误消息
                    if msg_type == 'error':
                        print(f"❌ 服务器返回错误: {msg_data}")
                        return False
                    
                    # 如果终端就绪，发送测试命令
                    if '就绪' in str(msg_data) or 'ready' in str(msg_data).lower():
                        print("🚀 终端就绪，发送测试命令")
                        await websocket.send(json.dumps({'command': 'whoami'}))
                        
                        # 等待命令响应
                        await asyncio.sleep(2)
                        return True
                        
            except asyncio.TimeoutError:
                print("⏰ WebSocket消息接收超时")
                return False
                
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket连接失败 - 状态码: {e.status_code}")
        return False
        
    except Exception as e:
        print(f"❌ WebSocket连接异常: {str(e)}")
        return False

async def main():
    """主函数"""
    print("🧪 简化WebSocket终端连接测试")
    print("=" * 50)
    
    # 1. 测试登录
    access_token = test_login()
    if not access_token:
        print("❌ 登录失败，无法继续测试")
        return False
    
    # 2. 获取服务器
    server_id = get_servers(access_token)
    if not server_id:
        print("❌ 没有可用服务器，无法测试WebSocket")
        return False
    
    # 3. 测试WebSocket连接
    print(f"\n🔌 开始WebSocket连接测试...")
    result = await test_websocket_with_auth(server_id, access_token)
    
    print("\n" + "=" * 50)
    if result:
        print("🎉 WebSocket终端连接测试成功！")
        return True
    else:
        print("💥 WebSocket终端连接测试失败！")
        return False

if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)