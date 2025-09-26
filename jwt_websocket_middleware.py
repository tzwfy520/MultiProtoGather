"""
JWT WebSocket认证中间件
用于在WebSocket连接中处理JWT令牌认证
"""

from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_string):
    """从JWT令牌获取用户"""
    try:
        # 验证并解码JWT令牌
        access_token = AccessToken(token_string)
        user_id = access_token['user_id']
        
        # 获取用户对象
        user = User.objects.get(id=user_id)
        return user
    except (InvalidToken, TokenError, User.DoesNotExist) as e:
        logger.warning(f"JWT令牌验证失败: {str(e)}")
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """JWT认证中间件"""
    
    async def __call__(self, scope, receive, send):
        # 只处理WebSocket连接
        if scope['type'] == 'websocket':
            # 从查询参数中获取token
            query_string = scope.get('query_string', b'').decode()
            query_params = parse_qs(query_string)
            
            token = None
            if 'token' in query_params:
                token = query_params['token'][0]
            else:
                # 从headers中获取Authorization
                headers = dict(scope.get('headers', []))
                auth_header = headers.get(b'authorization', b'').decode()
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:]  # 移除 'Bearer ' 前缀
            
            if token:
                # 验证JWT令牌并获取用户
                user = await get_user_from_token(token)
                scope['user'] = user
                logger.info(f"WebSocket JWT认证: 用户 {user.username if hasattr(user, 'username') else 'Anonymous'}")
            else:
                scope['user'] = AnonymousUser()
                logger.warning("WebSocket连接未提供JWT令牌")
        
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """JWT认证中间件栈"""
    return JWTAuthMiddleware(inner)