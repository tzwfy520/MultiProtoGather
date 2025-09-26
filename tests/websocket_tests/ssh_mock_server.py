#!/usr/bin/env python3
"""
功能完整的模拟SSH服务器
用于WebSocket终端功能测试
"""

import socket
import threading
import time
import logging
import base64
import hashlib
import struct
import os

logger = logging.getLogger(__name__)

class MockSSHServer:
    """模拟SSH服务器，支持基本的SSH协议交互"""
    
    def __init__(self, host='127.0.0.1', port=2222):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.clients = []
        
    def start(self):
        """启动模拟SSH服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            logger.info(f"模拟SSH服务器启动在 {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    logger.info(f"接收到连接: {addr}")
                    
                    # 为每个客户端创建处理线程
                    client_thread = threading.Thread(
                        target=self._handle_client, 
                        args=(client_socket, addr),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        logger.error(f"接受连接错误: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"启动模拟SSH服务器失败: {e}")
        finally:
            self.stop()
    
    def _handle_client(self, client_socket, addr):
        """处理客户端连接"""
        try:
            self.clients.append(client_socket)
            
            # 发送SSH版本字符串
            version_string = b"SSH-2.0-MockSSH_1.0\r\n"
            client_socket.send(version_string)
            logger.info(f"发送版本字符串到 {addr}")
            
            # 接收客户端版本字符串
            client_version = client_socket.recv(255)
            logger.info(f"收到客户端版本: {client_version.decode('utf-8', errors='ignore').strip()}")
            
            # 模拟SSH密钥交换过程
            self._simulate_key_exchange(client_socket)
            
            # 模拟用户认证过程
            if self._simulate_authentication(client_socket):
                # 认证成功，进入shell模式
                self._simulate_shell_session(client_socket, addr)
            
        except Exception as e:
            logger.error(f"处理客户端 {addr} 错误: {e}")
        finally:
            try:
                client_socket.close()
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
            except:
                pass
            logger.info(f"客户端 {addr} 连接已关闭")
    
    def _simulate_key_exchange(self, client_socket):
        """模拟SSH密钥交换"""
        try:
            # 发送服务器密钥交换初始化包
            kex_init = self._create_kex_init_packet()
            client_socket.send(kex_init)
            
            # 接收客户端密钥交换包
            client_kex = client_socket.recv(1024)
            logger.info(f"收到客户端密钥交换包: {len(client_kex)} 字节")
            
            # 发送Diffie-Hellman密钥交换回复
            dh_reply = self._create_dh_reply_packet()
            client_socket.send(dh_reply)
            
            # 接收客户端DH密钥交换
            client_dh = client_socket.recv(1024)
            logger.info(f"收到客户端DH包: {len(client_dh)} 字节")
            
            # 发送新密钥包
            newkeys = self._create_newkeys_packet()
            client_socket.send(newkeys)
            
            # 接收客户端新密钥包
            client_newkeys = client_socket.recv(1024)
            logger.info("密钥交换完成")
            
        except Exception as e:
            logger.error(f"密钥交换错误: {e}")
            raise
    
    def _simulate_authentication(self, client_socket):
        """模拟用户认证"""
        try:
            # 发送服务请求成功
            service_accept = self._create_service_accept_packet()
            client_socket.send(service_accept)
            
            # 接收认证请求
            auth_request = client_socket.recv(1024)
            logger.info(f"收到认证请求: {len(auth_request)} 字节")
            
            # 发送认证成功
            auth_success = self._create_auth_success_packet()
            client_socket.send(auth_success)
            logger.info("用户认证成功")
            
            return True
            
        except Exception as e:
            logger.error(f"认证过程错误: {e}")
            return False
    
    def _simulate_shell_session(self, client_socket, addr):
        """模拟shell会话"""
        try:
            logger.info(f"开始shell会话 {addr}")
            
            # 接收通道打开请求
            channel_open = client_socket.recv(1024)
            logger.info("收到通道打开请求")
            
            # 发送通道打开确认
            channel_confirm = self._create_channel_open_confirm()
            client_socket.send(channel_confirm)
            
            # 接收shell请求
            shell_request = client_socket.recv(1024)
            logger.info("收到shell请求")
            
            # 发送shell请求成功
            shell_success = self._create_channel_success()
            client_socket.send(shell_success)
            
            # 发送欢迎消息和提示符
            welcome_msg = self._create_channel_data(b"Welcome to MockSSH Server!\r\n")
            client_socket.send(welcome_msg)
            
            prompt = self._create_channel_data(b"mockuser@mockhost:~$ ")
            client_socket.send(prompt)
            
            # 处理shell命令
            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    # 解析SSH数据包
                    command = self._parse_channel_data(data)
                    if command:
                        logger.info(f"收到命令: {command}")
                        
                        # 回显命令
                        echo = self._create_channel_data(command.encode() + b"\r\n")
                        client_socket.send(echo)
                        
                        # 处理命令并发送响应
                        response = self._process_command(command.strip())
                        if response:
                            response_packet = self._create_channel_data(response.encode() + b"\r\n")
                            client_socket.send(response_packet)
                        
                        # 发送新的提示符
                        prompt = self._create_channel_data(b"mockuser@mockhost:~$ ")
                        client_socket.send(prompt)
                
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Shell会话错误: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Shell会话异常: {e}")
    
    def _process_command(self, command):
        """处理shell命令"""
        if command == "whoami":
            return "mockuser"
        elif command == "pwd":
            return "/home/mockuser"
        elif command == "ls":
            return "file1.txt  file2.txt  directory1"
        elif command.startswith("echo"):
            return command[5:]  # 返回echo后面的内容
        elif command == "date":
            return time.strftime("%Y-%m-%d %H:%M:%S")
        elif command == "uname -a":
            return "Linux mockhost 5.4.0 #1 SMP x86_64 GNU/Linux"
        elif command == "exit":
            return "logout"
        else:
            return f"bash: {command}: command not found"
    
    def _create_kex_init_packet(self):
        """创建密钥交换初始化包"""
        # 简化的KEX_INIT包
        packet_type = b'\x14'  # SSH_MSG_KEXINIT
        random_data = os.urandom(16)
        algorithms = b'diffie-hellman-group14-sha256,ssh-rsa,aes128-ctr,hmac-sha2-256'
        
        payload = packet_type + random_data + b'\x00' * 100  # 简化的算法列表
        length = struct.pack('>I', len(payload))
        
        return length + payload
    
    def _create_dh_reply_packet(self):
        """创建DH回复包"""
        packet_type = b'\x1f'  # SSH_MSG_KEXDH_REPLY
        server_key = b'\x00' * 100  # 模拟服务器公钥
        dh_f = b'\x00' * 100  # 模拟DH参数
        signature = b'\x00' * 100  # 模拟签名
        
        payload = packet_type + server_key + dh_f + signature
        length = struct.pack('>I', len(payload))
        
        return length + payload
    
    def _create_newkeys_packet(self):
        """创建新密钥包"""
        packet_type = b'\x15'  # SSH_MSG_NEWKEYS
        length = struct.pack('>I', 1)
        
        return length + packet_type
    
    def _create_service_accept_packet(self):
        """创建服务接受包"""
        packet_type = b'\x06'  # SSH_MSG_SERVICE_ACCEPT
        service_name = b'ssh-userauth'
        
        payload = packet_type + struct.pack('>I', len(service_name)) + service_name
        length = struct.pack('>I', len(payload))
        
        return length + payload
    
    def _create_auth_success_packet(self):
        """创建认证成功包"""
        packet_type = b'\x34'  # SSH_MSG_USERAUTH_SUCCESS
        length = struct.pack('>I', 1)
        
        return length + packet_type
    
    def _create_channel_open_confirm(self):
        """创建通道打开确认包"""
        packet_type = b'\x5b'  # SSH_MSG_CHANNEL_OPEN_CONFIRMATION
        recipient_channel = struct.pack('>I', 0)
        sender_channel = struct.pack('>I', 0)
        window_size = struct.pack('>I', 32768)
        max_packet_size = struct.pack('>I', 32768)
        
        payload = packet_type + recipient_channel + sender_channel + window_size + max_packet_size
        length = struct.pack('>I', len(payload))
        
        return length + payload
    
    def _create_channel_success(self):
        """创建通道请求成功包"""
        packet_type = b'\x63'  # SSH_MSG_CHANNEL_SUCCESS
        recipient_channel = struct.pack('>I', 0)
        
        payload = packet_type + recipient_channel
        length = struct.pack('>I', len(payload))
        
        return length + payload
    
    def _create_channel_data(self, data):
        """创建通道数据包"""
        packet_type = b'\x5e'  # SSH_MSG_CHANNEL_DATA
        recipient_channel = struct.pack('>I', 0)
        data_length = struct.pack('>I', len(data))
        
        payload = packet_type + recipient_channel + data_length + data
        length = struct.pack('>I', len(payload))
        
        return length + payload
    
    def _parse_channel_data(self, packet):
        """解析通道数据包"""
        try:
            if len(packet) < 4:
                return None
            
            length = struct.unpack('>I', packet[:4])[0]
            if len(packet) < 4 + length:
                return None
            
            payload = packet[4:4+length]
            if len(payload) < 1:
                return None
            
            packet_type = payload[0]
            if packet_type == 0x5e:  # SSH_MSG_CHANNEL_DATA
                if len(payload) >= 9:
                    data_length = struct.unpack('>I', payload[5:9])[0]
                    if len(payload) >= 9 + data_length:
                        return payload[9:9+data_length].decode('utf-8', errors='ignore')
            
            return None
            
        except Exception as e:
            logger.error(f"解析数据包错误: {e}")
            return None
    
    def stop(self):
        """停止模拟SSH服务器"""
        self.running = False
        
        # 关闭所有客户端连接
        for client in self.clients[:]:
            try:
                client.close()
            except:
                pass
        self.clients.clear()
        
        # 关闭服务器socket
        if self.server_socket:
            try:
                self.server_socket.close()
                logger.info("模拟SSH服务器已停止")
            except:
                pass

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 启动模拟SSH服务器
    server = MockSSHServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        server.stop()