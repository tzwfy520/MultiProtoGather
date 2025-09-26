"""
服务器状态检测定时任务
"""
import socket
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from celery import shared_task
from .models import ServerResource, ServerStatusHistory

logger = logging.getLogger(__name__)


@shared_task
def check_all_servers_status():
    """检查所有服务器状态的定时任务"""
    logger.info("开始执行服务器状态检测任务")
    
    # 获取所有激活的服务器
    servers = ServerResource.objects.filter(is_active=True)
    
    for server in servers:
        check_single_server_status.delay(server.id)
    
    logger.info(f"已为 {servers.count()} 台服务器启动状态检测任务")


@shared_task
def check_single_server_status(server_id):
    """检查单个服务器状态"""
    try:
        from resources.models import ServerResource, ServerStatusHistory
        from django.utils import timezone
        import socket
        
        server = ServerResource.objects.get(id=server_id)
        
        # TCP端口探测，2秒超时
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((server.ip_address, server.port))
        sock.close()
        
        old_status = server.status
        
        if result == 0:
            # 连接成功，服务器在线
            server.status = 'online'
            server.last_online_time = timezone.now()
            server.save()
            
            # 清除连续失败计数
            clear_consecutive_failures(server_id)
            
            # 记录状态历史
            if old_status != 'online':
                ServerStatusHistory.objects.create(
                    server=server,
                    old_status=old_status,
                    new_status='online',
                    check_time=timezone.now()
                )
        else:
            # 连接失败，增加失败计数
            failure_count = increment_consecutive_failures(server_id)
            
            # 连续3次失败后标记为离线
            if failure_count >= 3:
                server.status = 'offline'
                server.save()
                
                # 记录状态历史
                if old_status != 'offline':
                    ServerStatusHistory.objects.create(
                        server=server,
                        old_status=old_status,
                        new_status='offline',
                        error_message=f'连续{failure_count}次连接失败',
                        check_time=timezone.now()
                    )
        
        return True
        
    except Exception as e:
        # 异常情况下也增加失败计数
        failure_count = increment_consecutive_failures(server_id)
        
        if failure_count >= 3:
            try:
                server = ServerResource.objects.get(id=server_id)
                old_status = server.status
                server.status = 'offline'
                server.save()
                
                # 记录状态历史
                if old_status != 'offline':
                    ServerStatusHistory.objects.create(
                        server=server,
                        old_status=old_status,
                        new_status='offline',
                        error_message=f'检测异常: {str(e)}',
                        check_time=timezone.now()
                    )
            except:
                pass
        
        return False


def get_recent_failure_count(server):
    """获取最近的连续失败次数"""
    # 获取最近10分钟内的状态历史，按时间倒序
    recent_time = timezone.now() - timedelta(minutes=10)
    recent_history = ServerStatusHistory.objects.filter(
        server=server,
        changed_at__gte=recent_time
    ).order_by('-changed_at')
    
    failure_count = 0
    for history in recent_history:
        if history.status == 'offline':
            failure_count += 1
        else:
            # 遇到在线状态就停止计数
            break
    
    return failure_count


def handle_connection_failure(server, recent_failures, error_message):
    """处理连接失败的情况"""
    failure_count = recent_failures + 1
    
    # 记录失败历史
    ServerStatusHistory.objects.create(
        server=server,
        status='offline',
        changed_by=None,  # 系统自动检测
        notes=f'定期状态检测失败 (第{failure_count}次): {error_message}'
    )
    
    # 如果连续失败3次或以上，标记为离线
    if failure_count >= 3:
        old_status = server.status
        server.status = 'offline'
        server.response_time = None
        server.save()
        
        if old_status != 'offline':
            logger.warning(f"服务器 {server.name} ({server.ip_address}) 连续失败{failure_count}次，标记为离线")
            
            # 记录状态变更
            ServerStatusHistory.objects.create(
                server=server,
                status='offline',
                changed_by=None,
                notes=f'连续失败{failure_count}次，自动标记为离线'
            )
    else:
        logger.debug(f"服务器 {server.name} ({server.ip_address}) 检测失败 (第{failure_count}次): {error_message}")


@shared_task
def cleanup_old_status_history():
    """清理旧的状态历史记录"""
    # 删除30天前的状态历史记录
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = ServerStatusHistory.objects.filter(
        changed_at__lt=cutoff_date
    ).delete()[0]
    
    if deleted_count > 0:
        logger.info(f"清理了 {deleted_count} 条旧的状态历史记录")
    
    return deleted_count