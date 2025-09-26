"""
Celery配置文件
"""
import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'multiprotgather_backend.settings')

# 创建Celery应用
app = Celery('multiprotgather')

# 从Django设置中加载配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks()

# 定时任务配置
app.conf.beat_schedule = {
    # 服务器状态检测任务 - 每30秒执行一次
    'check-servers-status': {
        'task': 'resources.tasks.check_all_servers_status',
        'schedule': 30.0,  # 30秒
        'options': {
            'expires': 25,  # 任务过期时间，避免堆积
        }
    },
    # 清理旧状态历史记录 - 每天凌晨2点执行
    'cleanup-old-status-history': {
        'task': 'resources.tasks.cleanup_old_status_history',
        'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点
    },
}

# 时区设置
app.conf.timezone = 'Asia/Shanghai'

# 任务路由配置
app.conf.task_routes = {
    'resources.tasks.check_all_servers_status': {'queue': 'status_check'},
    'resources.tasks.check_single_server_status': {'queue': 'status_check'},
    'resources.tasks.cleanup_old_status_history': {'queue': 'maintenance'},
}

# 队列配置
app.conf.task_default_queue = 'default'
app.conf.task_queues = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'status_check': {
        'exchange': 'status_check',
        'routing_key': 'status_check',
    },
    'maintenance': {
        'exchange': 'maintenance',
        'routing_key': 'maintenance',
    },
}

# 任务执行配置
app.conf.task_soft_time_limit = 60  # 软超时60秒
app.conf.task_time_limit = 120      # 硬超时120秒
app.conf.worker_prefetch_multiplier = 1  # 每次只预取一个任务
app.conf.task_acks_late = True      # 任务完成后才确认
app.conf.worker_disable_rate_limits = False

@app.task(bind=True)
def debug_task(self):
    """调试任务"""
    print(f'Request: {self.request!r}')