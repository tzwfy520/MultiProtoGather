#!/usr/bin/env python3
"""
测试直接交互终端功能
包括字符级别输入、特殊键处理和交互式程序支持
"""

import asyncio
import websockets
import json
import time
import sys
import os

# 配置Django设置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'multiprotgather_backend.settings')

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import django
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from resources.models import ServerResource
from asgiref.sync import sync_to_async
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InteractiveTerminalTest:
    def __init__(self):
        self.ws_url = "ws://localhost:8000/ws/terminal/"
        self.access_token = None
        self.server_id = None
        
    async def setup_test_environment(self):
        """设置测试环境"""
        try:
            User = get_user_model()
            
            # 创建测试用户（如果不存在）
            try:
                self.user = await sync_to_async(User.objects.get)(username='test_user')
            except User.DoesNotExist:
                self.user = await sync_to_async(User.objects.create_user)(
                    username='test_user',
                    password='test_password',
                    email='test@example.com'
                )
            
            # 创建测试服务器（如果不存在）
            try:
                self.server = await sync_to_async(ServerResource.objects.get)(
                    ip_address='127.0.0.1',
                    port=22
                )
            except ServerResource.DoesNotExist:
                self.server = await sync_to_async(ServerResource.objects.create)(
                    name='Interactive Test Server',
                    ip_address='127.0.0.1',
                    port=22,
                    username='eccom123',
                    password='password123',  # 实际测试时需要有效密码
                    os_type='linux',
                    description='交互式终端测试服务器'
                )
            
            # 生成JWT token
            refresh = RefreshToken.for_user(self.user)
            self.jwt_token = str(refresh.access_token)
            
            logger.info(f"测试环境设置完成 - 用户: {self.user.username}, 服务器: {self.server.name}")
            return True
            
        except Exception as e:
            logger.error(f"设置测试环境失败: {e}")
            return False
    
    async def test_websocket_connection(self):
        """测试WebSocket连接"""
        try:
            ws_url = f"{self.ws_url}{self.server.id}/?token={self.jwt_token}"
            logger.info(f"连接到: {ws_url}")
            
            async with websockets.connect(ws_url) as websocket:
                logger.info("WebSocket连接成功")
                
                # 等待初始化消息
                await asyncio.sleep(2)
                
                # 检查是否有初始消息
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    logger.info(f"收到初始消息: {data}")
                except asyncio.TimeoutError:
                    logger.info("没有收到初始消息")
                
                return websocket
                
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            return None
    
    async def test_character_input(self, websocket):
        """测试字符级别输入"""
        logger.info("测试字符级别输入...")
        
        # 测试普通字符输入
        test_chars = ['h', 'e', 'l', 'l', 'o']
        for char in test_chars:
            message = {
                'type': 'input',
                'data': char
            }
            await websocket.send(json.dumps(message))
            logger.info(f"发送字符: {char}")
            await asyncio.sleep(0.1)
        
        # 发送回车
        message = {
            'type': 'input', 
            'data': '\r'
        }
        await websocket.send(json.dumps(message))
        logger.info("发送回车")
        
        # 等待响应
        await asyncio.sleep(1)
        
        # 接收输出
        try:
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                data = json.loads(message)
                if data.get('type') == 'output':
                    logger.info(f"收到输出: {repr(data.get('data', ''))}")
        except asyncio.TimeoutError:
            pass
    
    async def test_special_keys(self, websocket):
        """测试特殊键处理"""
        logger.info("测试特殊键处理...")
        
        # 测试方向键
        special_keys = [
            ('ArrowUp', '\x1b[A'),
            ('ArrowDown', '\x1b[B'),
            ('ArrowLeft', '\x1b[D'),
            ('ArrowRight', '\x1b[C'),
            ('Tab', '\t'),
            ('Backspace', '\x7f')
        ]
        
        for key_name, key_sequence in special_keys:
            message = {
                'type': 'key',
                'data': key_sequence
            }
            await websocket.send(json.dumps(message))
            logger.info(f"发送特殊键: {key_name} -> {repr(key_sequence)}")
            await asyncio.sleep(0.2)
            
            # 接收可能的响应
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=0.3)
                data = json.loads(message)
                if data.get('type') == 'output':
                    logger.info(f"特殊键响应: {repr(data.get('data', ''))}")
            except asyncio.TimeoutError:
                pass
    
    async def test_control_keys(self, websocket):
        """测试控制键组合"""
        logger.info("测试控制键组合...")
        
        # 测试Ctrl+C (中断)
        message = {
            'type': 'key',
            'data': '\x03'  # Ctrl+C
        }
        await websocket.send(json.dumps(message))
        logger.info("发送Ctrl+C")
        await asyncio.sleep(0.5)
        
        # 接收响应
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
            data = json.loads(message)
            if data.get('type') == 'output':
                logger.info(f"Ctrl+C响应: {repr(data.get('data', ''))}")
        except asyncio.TimeoutError:
            logger.info("Ctrl+C没有响应")
    
    async def test_interactive_program(self, websocket):
        """测试交互式程序 (如果可用)"""
        logger.info("测试交互式程序...")
        
        # 尝试运行简单的交互式命令
        commands = [
            "echo 'Interactive test'",
            "pwd",
            "whoami"
        ]
        
        for cmd in commands:
            logger.info(f"执行命令: {cmd}")
            
            # 发送命令字符
            for char in cmd:
                message = {
                    'type': 'input',
                    'data': char
                }
                await websocket.send(json.dumps(message))
                await asyncio.sleep(0.05)
            
            # 发送回车
            message = {
                'type': 'input',
                'data': '\r'
            }
            await websocket.send(json.dumps(message))
            
            # 等待命令执行
            await asyncio.sleep(1)
            
            # 接收输出
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    data = json.loads(message)
                    if data.get('type') == 'output':
                        logger.info(f"命令输出: {repr(data.get('data', ''))}")
            except asyncio.TimeoutError:
                pass
    
    async def test_terminal_resize(self, websocket):
        """测试终端大小调整"""
        try:
            logger.info("测试终端大小调整...")
            
            # 发送终端大小调整消息
            resize_message = {
                "type": "resize",
                "cols": 120,
                "rows": 40
            }
            
            await websocket.send(json.dumps(resize_message))
            logger.info("✅ 终端大小调整消息发送成功")
            
            # 等待一下让服务器处理
            await asyncio.sleep(0.5)
            
            return True
            
        except Exception as e:
            logger.error(f"终端大小调整测试失败: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始交互式终端测试...")
        
        # 设置测试环境
        if not await self.setup_test_environment():
            logger.error("测试环境设置失败")
            return False
        
        # 建立WebSocket连接
        websocket = await self.test_websocket_connection()
        if not websocket:
            logger.error("WebSocket连接失败")
            return False
        
        try:
            # 运行各项测试
            tests = [
                ("终端大小调整", self.test_terminal_resize),
                ("字符输入", self.test_character_input),
                ("特殊按键", self.test_special_keys),
                ("控制键", self.test_control_keys),
                ("交互式程序", self.test_interactive_program)
            ]
            
            for test_name, test_func in tests:
                logger.info(f"开始测试: {test_name}")
                try:
                    if hasattr(test_func, '__code__') and test_func.__code__.co_argcount > 1:
                        # 如果测试函数需要websocket参数
                        result = await test_func(websocket)
                    else:
                        # 如果测试函数不需要额外参数
                        result = await test_func()
                    
                    if result:
                        logger.info(f"✅ {test_name} 测试通过")
                    else:
                        logger.error(f"❌ {test_name} 测试失败")
                        
                except Exception as e:
                    logger.error(f"❌ {test_name} 测试异常: {e}")
            
            logger.info("🎉 所有测试完成")
            return True
            
        except Exception as e:
            logger.error(f"测试过程中出错: {e}")
            return False
        
        finally:
            await websocket.close()

def main():
    """主函数"""
    # 运行测试
    test = InteractiveTerminalTest()
    
    try:
        result = asyncio.run(test.run_all_tests())
        if result:
            logger.info("✅ 交互式终端测试通过")
            sys.exit(0)
        else:
            logger.error("❌ 交互式终端测试失败")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试运行失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()