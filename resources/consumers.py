import json
import asyncio
import paramiko
import threading
import time
import queue
import re
import socket
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ServerResource
from core.utils import decrypt_password
import logging

logger = logging.getLogger(__name__)


class SSHTerminalConsumer(AsyncWebsocketConsumer):
    """SSH终端WebSocket消费者"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssh_client = None
        self.ssh_channel = None
        self.server_id = None
        self.server = None
        self.read_thread = None
        self.connected = False
        self.terminal_ready = False
        self.output_queue = queue.Queue()
        self.queue_processor_task = None
    
    async def connect(self):
        """WebSocket连接"""
        self.server_id = self.scope['url_route']['kwargs']['server_id']
        
        # 检查用户认证
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            logger.warning(f"未认证用户尝试连接WebSocket: {self.scope.get('client')}")
            await self.close(code=4001)
            return
        
        await self.accept()
        logger.info(f"WebSocket连接已建立，用户: {user.username}, 服务器ID: {self.server_id}")
        
        # 设置连接状态为True
        self.connected = True
        logger.info(f"设置连接状态: {self.connected}")
        
        # 启动队列处理任务
        logger.info("正在启动队列处理任务")
        self.queue_processor_task = asyncio.create_task(self._process_output_queue())
        logger.info(f"队列处理任务已创建: {self.queue_processor_task}")
        
        # 获取服务器信息并建立SSH连接
        try:
            self.server = await self.get_server(self.server_id)
            if self.server:
                await self.send_message(f"正在连接到 {self.server.name} ({self.server.ip_address})...")
                success = await self.establish_ssh_connection()
                if success:
                    await self.send_message("SSH连接已建立，正在初始化终端...")
                    await self.initialize_terminal()
                else:
                    await self.send_error("SSH连接失败")
            else:
                await self.send_error("服务器不存在")
        except Exception as e:
            logger.error(f"WebSocket连接错误: {str(e)}")
            await self.send_error(f"连接失败: {str(e)}")
    
    async def disconnect(self, close_code):
        """WebSocket断开连接"""
        logger.info(f"WebSocket断开连接: {close_code}")
        self.connected = False
        self.terminal_ready = False
        
        # 停止队列处理任务
        if self.queue_processor_task:
            self.queue_processor_task.cancel()
            try:
                await self.queue_processor_task
            except asyncio.CancelledError:
                pass
        
        # 等待读取线程结束
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2)
        
        # 关闭SSH连接
        if self.ssh_channel:
            try:
                self.ssh_channel.close()
            except:
                pass
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except:
                pass
    
    async def receive(self, text_data):
        """接收WebSocket消息"""
        try:
            data = json.loads(text_data)
            msg_type = data.get('type', '')
            
            if not self.terminal_ready:
                await self.send_error("终端未就绪，请等待连接完成")
                return
            
            # 处理不同类型的消息
            if msg_type == 'input':
                # 处理字符级输入 - 直接交互模式
                input_data = data.get('data', '')
                if self.ssh_channel and input_data:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._send_input, input_data
                    )
            elif msg_type == 'key':
                # 处理特殊按键（方向键、功能键等）
                key_data = data.get('data', '')
                if self.ssh_channel and key_data:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._send_key, key_data
                    )
            elif msg_type == 'command':
                # 兼容旧的命令模式
                command = data.get('data', '')
                if self.ssh_channel and command:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._send_command, command
                    )
            elif msg_type == 'resize':
                # 处理终端大小调整
                width = data.get('width', 80)
                height = data.get('height', 24)
                if self.ssh_channel:
                    try:
                        self.ssh_channel.resize_pty(width=width, height=height)
                        logger.info(f"终端大小已调整: {width}x{height}")
                    except Exception as e:
                        logger.error(f"调整终端大小失败: {str(e)}")
            else:
                # 兼容旧格式 - 直接发送command字段
                command = data.get('command', '')
                if self.ssh_channel and command:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._send_command, command
                    )
                    
        except Exception as e:
            logger.error(f"接收消息错误: {str(e)}")
            await self.send_error(f"消息处理失败: {str(e)}")
    
    def _clean_ansi_sequences(self, text):
        """处理ANSI转义序列 - 保留原始输出让前端处理"""
        # 不再删除ANSI序列，而是保留原始输出
        # 前端将负责正确解析和渲染这些序列
        return text
    
    def _send_input(self, input_data):
        """发送用户输入到SSH"""
        try:
            if self.ssh_channel and not self.ssh_channel.closed:
                # 检查SSH连接状态
                if not self.ssh_client or not self.ssh_client.get_transport() or not self.ssh_client.get_transport().is_active():
                    logger.error("SSH连接已断开，无法发送输入")
                    return
                
                logger.info(f"发送输入: {repr(input_data)}")
                self.ssh_channel.send(input_data)
            else:
                logger.error("SSH通道不可用，无法发送输入")
        except Exception as e:
            logger.error(f"发送输入失败: {str(e)} (类型: {type(e).__name__})")
            # 检查连接状态
            if self.ssh_client and self.ssh_client.get_transport():
                logger.error(f"SSH传输状态: active={self.ssh_client.get_transport().is_active()}")
            if self.ssh_channel:
                logger.error(f"SSH通道状态: active={self.ssh_channel.active}, closed={self.ssh_channel.closed}")
            # 不要在这里发送错误消息到WebSocket，避免循环
    
    def _send_key(self, key_data):
        """发送特殊按键到SSH通道"""
        try:
            if self.ssh_channel and not self.ssh_channel.closed:
                logger.info(f"发送按键: {key_data}")
                
                # 处理特殊按键映射
                key_mappings = {
                    'ArrowUp': '\x1b[A',
                    'ArrowDown': '\x1b[B', 
                    'ArrowRight': '\x1b[C',
                    'ArrowLeft': '\x1b[D',
                    'Home': '\x1b[H',
                    'End': '\x1b[F',
                    'PageUp': '\x1b[5~',
                    'PageDown': '\x1b[6~',
                    'Delete': '\x1b[3~',
                    'Insert': '\x1b[2~',
                    'F1': '\x1bOP',
                    'F2': '\x1bOQ',
                    'F3': '\x1bOR',
                    'F4': '\x1bOS',
                    'F5': '\x1b[15~',
                    'F6': '\x1b[17~',
                    'F7': '\x1b[18~',
                    'F8': '\x1b[19~',
                    'F9': '\x1b[20~',
                    'F10': '\x1b[21~',
                    'F11': '\x1b[23~',
                    'F12': '\x1b[24~',
                    'Tab': '\t',
                    'Enter': '\r',
                    'Backspace': '\x7f',
                    'Escape': '\x1b',
                }
                
                # 发送对应的控制序列
                if key_data in key_mappings:
                    self.ssh_channel.send(key_mappings[key_data])
                else:
                    # 如果不是特殊按键，直接发送
                    self.ssh_channel.send(key_data)
            else:
                logger.error("SSH通道不可用")
        except Exception as e:
            logger.error(f"发送按键失败: {str(e)}")
            # 不要在这里发送错误消息到WebSocket，避免循环

    def _send_command(self, command):
        """在线程中发送命令（兼容旧模式）"""
        try:
            if self.ssh_channel and not self.ssh_channel.closed:
                logger.info(f"发送命令: {command}")
                # 确保命令以换行符结尾
                if not command.endswith('\n'):
                    command += '\n'
                self.ssh_channel.send(command)
                logger.info(f"命令已发送: {repr(command)}")
            else:
                logger.error("SSH通道不可用")
        except Exception as e:
            logger.error(f"发送命令失败: {str(e)}")
            # 不要在这里发送错误消息到WebSocket，避免循环
    
    @database_sync_to_async
    def get_server(self, server_id):
        """获取服务器信息"""
        try:
            return ServerResource.objects.get(id=server_id)
        except ServerResource.DoesNotExist:
            return None
    
    async def establish_ssh_connection(self):
        """建立SSH连接"""
        try:
            # 在线程池中建立SSH连接
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._connect_ssh)
            
            if success and self.ssh_client:
                self.connected = True
                logger.info(f"SSH连接成功: {self.server.ip_address}")
                return True
            else:
                logger.error(f"SSH连接失败: {self.server.ip_address}")
                return False
                
        except Exception as e:
            logger.error(f"SSH连接异常: {str(e)}")
            await self.send_error(f"SSH连接错误: {str(e)}")
            return False
    
    def _connect_ssh(self):
        """在线程中建立SSH连接"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 准备连接参数 - 减少超时时间以快速失败
            connect_params = {
                'hostname': self.server.ip_address,
                'port': self.server.port,
                'username': self.server.username,
                'timeout': 15,  # 增加连接超时时间
                'banner_timeout': 20,  # 增加banner超时时间
                'auth_timeout': 15,  # 增加认证超时时间
                'look_for_keys': False,  # 不自动查找密钥文件
                'allow_agent': False  # 不使用SSH代理
            }
            
            # 根据认证方式添加参数
            if self.server.password:
                connect_params['password'] = decrypt_password(self.server.password)
            elif self.server.private_key:
                from io import StringIO
                try:
                    # 尝试不同的私钥格式
                    private_key = None
                    key_data = self.server.private_key
                    
                    # 尝试RSA密钥
                    try:
                        private_key = paramiko.RSAKey.from_private_key(StringIO(key_data))
                    except:
                        # 尝试DSS密钥
                        try:
                            private_key = paramiko.DSSKey.from_private_key(StringIO(key_data))
                        except:
                            # 尝试ECDSA密钥
                            try:
                                private_key = paramiko.ECDSAKey.from_private_key(StringIO(key_data))
                            except:
                                # 尝试Ed25519密钥
                                private_key = paramiko.Ed25519Key.from_private_key(StringIO(key_data))
                    
                    connect_params['pkey'] = private_key
                except Exception as e:
                    raise Exception(f"私钥格式错误: {str(e)}")
            else:
                # 如果没有密码和私钥，尝试使用空密码（某些测试服务器可能允许）
                connect_params['password'] = ''
            
            # 建立连接
            logger.info(f"正在连接SSH: {connect_params['hostname']}:{connect_params['port']}")
            self.ssh_client.connect(**connect_params)
            
            # 设置保活参数
            transport = self.ssh_client.get_transport()
            if transport:
                transport.set_keepalive(30)  # 每30秒发送保活包
            
            # 创建交互式shell - 启用PTY支持
            self.ssh_channel = self.ssh_client.invoke_shell(
                term='xterm-256color',
                width=80,
                height=24
            )
            
            # 设置通道参数以支持实时交互
            self.ssh_channel.settimeout(0.5)
            
            # 启用PTY模式，支持交互式程序
            # 这对于vim、nano等全屏应用程序是必需的
            logger.info(f"SSH通道已创建，PTY模式已启用")
            logger.info(f"通道状态: active={self.ssh_channel.active}, closed={self.ssh_channel.closed}")
            
            # 等待通道准备就绪
            time.sleep(1.0)  # 增加等待时间
            
            return True
            
        except paramiko.AuthenticationException as e:
            logger.error(f"SSH认证失败: {str(e)}")
            if self.ssh_client:
                try:
                    self.ssh_client.close()
                except:
                    pass
            raise Exception(f"认证失败: 用户名或密码错误")
        except paramiko.SSHException as e:
            logger.error(f"SSH协议错误: {str(e)}")
            if self.ssh_client:
                try:
                    self.ssh_client.close()
                except:
                    pass
            raise Exception(f"SSH协议错误: {str(e)}")
        except Exception as e:
            logger.error(f"SSH连接失败: {str(e)}")
            if self.ssh_client:
                try:
                    self.ssh_client.close()
                except:
                    pass
            # 检查是否是网络连接问题
            if "timed out" in str(e).lower():
                raise Exception(f"连接超时: 无法连接到 {self.server.ip_address}:{self.server.port}")
            elif "connection refused" in str(e).lower():
                raise Exception(f"连接被拒绝: {self.server.ip_address}:{self.server.port} 可能未开启SSH服务")
            else:
                raise Exception(f"连接失败: {str(e)}")
    
    async def initialize_terminal(self):
        """初始化终端"""
        try:
            # 等待终端准备就绪
            await asyncio.sleep(1)
            
            # 启动输出读取线程
            self.read_thread = threading.Thread(target=self._read_ssh_output, daemon=True)
            self.read_thread.start()
            
            # 发送初始命令获取提示符
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_initial_commands
            )
            
            self.terminal_ready = True
            await self.send_message("终端已就绪，可以开始输入命令")
            
        except Exception as e:
            logger.error(f"终端初始化失败: {str(e)}")
            await self.send_error(f"终端初始化失败: {str(e)}")
    
    def _send_initial_commands(self):
        """发送初始命令"""
        try:
            if self.ssh_channel:
                logger.info("发送初始命令设置终端环境")
                
                # 发送一个空行获取提示符
                self.ssh_channel.send('\n')
                time.sleep(0.5)
                
                # 设置环境变量
                self.ssh_channel.send('export TERM=xterm-256color\n')
                time.sleep(0.2)
                
                # 设置PS1提示符
                self.ssh_channel.send('export PS1="\\u@\\h:\\w$ "\n')
                time.sleep(0.2)
                
                # 发送一个测试命令确保终端响应
                self.ssh_channel.send('echo "Terminal Ready"\n')
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"发送初始命令失败: {str(e)}")
    
    def _read_ssh_output(self):
        """读取SSH输出的线程函数"""
        logger.info("SSH输出读取线程开始")
        consecutive_errors = 0
        max_consecutive_errors = 20  # 增加到20次
        buffer = b''
        
        while self.ssh_channel and not self.ssh_channel.closed:
            try:
                # 检查通道是否有数据可读
                if not self.ssh_channel.recv_ready():
                    time.sleep(0.1)  # 短暂等待
                    continue
                
                # 设置较长的超时时间
                self.ssh_channel.settimeout(2.0)  # 增加到2秒
                
                # 尝试接收数据
                data = self.ssh_channel.recv(4096)
                
                if data:
                    buffer += data
                    consecutive_errors = 0  # 重置错误计数
                    
                    # 处理缓冲区中的数据
                    while b'\n' in buffer or len(buffer) > 1024:
                        if b'\n' in buffer:
                            line, buffer = buffer.split(b'\n', 1)
                            line += b'\n'
                        else:
                            line = buffer
                            buffer = b''
                        
                        try:
                            decoded_line = line.decode('utf-8', errors='replace')
                            logger.info(f"SSH输出: '{decoded_line.strip()}'")
                            self.output_queue.put(('output', decoded_line))
                        except Exception as e:
                            logger.error(f"解码SSH输出时出错: {e}")
                            self.output_queue.put(('error', f"输出解码错误: {e}"))
                else:
                    # 没有数据，可能连接已关闭
                    time.sleep(0.1)
                    
            except socket.timeout:
                consecutive_errors += 1
                if consecutive_errors <= max_consecutive_errors:
                    logger.debug(f"SSH读取超时 (连续错误: {consecutive_errors})")
                else:
                    logger.error(f"连续超时错误过多({consecutive_errors})，停止读取SSH输出")
                    break
                    
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"读取SSH输出时出错: {e} (类型: {type(e).__name__}) (连续错误: {consecutive_errors})")
                
                # 检查SSH连接状态
                if self.ssh_transport:
                    logger.error(f"SSH传输状态: active={self.ssh_transport.is_active()}")
                if self.ssh_channel:
                    logger.error(f"SSH通道状态: active={self.ssh_channel.active}, closed={self.ssh_channel.closed}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"连续错误过多({consecutive_errors})，停止读取SSH输出")
                    break
                    
                time.sleep(0.1)
        
        # 处理剩余的缓冲区数据
        if buffer:
            try:
                decoded_buffer = buffer.decode('utf-8', errors='replace')
                logger.info(f"SSH输出(剩余): '{decoded_buffer.strip()}'")
                self.output_queue.put(('output', decoded_buffer))
            except Exception as e:
                logger.error(f"解码剩余SSH输出时出错: {e}")
        
        logger.info("SSH输出读取线程结束")
    
    async def send_message(self, message):
        """发送普通消息"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'data': message
        }))
    
    async def send_output(self, output):
        """发送SSH输出"""
        await self.send(text_data=json.dumps({
            'type': 'output',
            'data': output
        }))
    
    async def send_error(self, error):
        """发送错误消息"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'data': error
        }))
    
    async def send_output_message(self, event):
        """处理来自channel layer的输出消息"""
        await self.send_output(event['output'])
    
    async def send_error_message(self, event):
        """处理来自channel layer的错误消息"""
        await self.send_error(event['error'])
    
    async def _process_output_queue(self):
        """处理输出队列的异步任务"""
        logger.info("开始处理输出队列")
        while self.connected:
            try:
                # 非阻塞地获取队列中的消息
                try:
                    message_type, content = self.output_queue.get_nowait()
                    logger.info(f"从队列获取消息: {message_type}, 内容: {repr(content[:100])}")
                    if message_type == 'output':
                        await self.send_output(content)
                        logger.info("输出消息已发送")
                    elif message_type == 'error':
                        await self.send_error(content)
                        logger.info("错误消息已发送")
                    self.output_queue.task_done()
                except queue.Empty:
                    # 队列为空，短暂休眠
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"处理输出队列错误: {str(e)}")
                await asyncio.sleep(0.1)
        logger.info("输出队列处理结束")