#!/usr/bin/env python3
"""
使用paramiko的模拟SSH服务器，用于测试终端功能
"""
import paramiko
import threading
import socket
import os
import sys
import time

class MockSSHServer:
    def __init__(self, host='127.0.0.1', port=2222):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        self.host_key = None
        
        # 生成临时主机密钥
        self.host_key = paramiko.RSAKey.generate(2048)
        
    def start(self):
        """启动模拟SSH服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"模拟SSH服务器启动在 {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    print(f"客户端连接: {addr}")
                    
                    # 创建线程处理客户端
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"接受连接时出错: {e}")
                    break
                    
        except Exception as e:
            print(f"启动服务器失败: {e}")
        finally:
            self.stop()
    
    def handle_client(self, client_socket, addr):
        """处理客户端连接"""
        try:
            # 创建SSH传输层
            transport = paramiko.Transport(client_socket)
            transport.add_server_key(self.host_key)
            
            # 创建服务器接口
            server = MockSSHServerInterface()
            transport.set_subsystem_handler('sftp', paramiko.SFTPServer)
            
            # 启动服务器
            transport.start_server(server=server)
            
            # 等待认证
            channel = transport.accept(20)
            if channel is None:
                print(f"客户端 {addr} 认证失败")
                return
                
            print(f"客户端 {addr} 认证成功")
            
            # 处理shell会话
            self.handle_shell(channel, addr)
            
        except Exception as e:
            print(f"处理客户端 {addr} 时出错: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            print(f"客户端 {addr} 断开连接")
    
    def handle_shell(self, channel, addr):
        """处理shell会话"""
        try:
            # 发送欢迎信息
            channel.send("Welcome to Mock SSH Server!\r\n")
            channel.send("testuser@mockserver:~$ ")
            
            command_buffer = ""
            
            while True:
                try:
                    data = channel.recv(1024)
                    if not data:
                        break
                    
                    # 处理输入
                    for byte in data:
                        char = chr(byte)
                        
                        if char == '\r' or char == '\n':
                            # 执行命令
                            if command_buffer.strip():
                                response = self.execute_command(command_buffer.strip())
                                channel.send(f"\r\n{response}\r\n")
                            channel.send("testuser@mockserver:~$ ")
                            command_buffer = ""
                        elif char == '\x7f' or char == '\x08':  # 退格键
                            if command_buffer:
                                command_buffer = command_buffer[:-1]
                                channel.send('\b \b')
                        elif char == '\x03':  # Ctrl+C
                            channel.send("^C\r\n")
                            channel.send("testuser@mockserver:~$ ")
                            command_buffer = ""
                        elif char == '\x04':  # Ctrl+D (EOF)
                            channel.send("logout\r\n")
                            break
                        elif ord(char) >= 32:  # 可打印字符
                            command_buffer += char
                            channel.send(char)
                            
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Shell处理错误: {e}")
                    break
                    
        except Exception as e:
            print(f"Shell会话错误: {e}")
        finally:
            channel.close()
    
    def execute_command(self, command):
        """执行命令并返回结果"""
        command = command.strip()
        
        if command == "ls":
            return "file1.txt  file2.txt  directory1  directory2"
        elif command == "pwd":
            return "/home/testuser"
        elif command == "whoami":
            return "testuser"
        elif command.startswith("echo "):
            return command[5:]  # 返回echo后面的内容
        elif command == "date":
            return time.strftime("%a %b %d %H:%M:%S %Z %Y")
        elif command == "exit":
            return "logout"
        elif command == "help":
            return "Available commands: ls, pwd, whoami, echo, date, exit, help"
        else:
            return f"bash: {command}: command not found"
    
    def stop(self):
        """停止服务器"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print("模拟SSH服务器已停止")

class MockSSHServerInterface(paramiko.ServerInterface):
    """SSH服务器接口实现"""
    
    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
    
    def check_auth_password(self, username, password):
        # 简单的认证：用户名testuser，密码testpass
        if username == 'testuser' and password == 'testpass':
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED
    
    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_FAILED
    
    def get_allowed_auths(self, username):
        return 'password'
    
    def check_channel_shell_request(self, channel):
        return True
    
    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

def main():
    """主函数"""
    server = MockSSHServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止服务器...")
        server.stop()
    except Exception as e:
        print(f"服务器运行出错: {e}")
        server.stop()

if __name__ == "__main__":
    main()