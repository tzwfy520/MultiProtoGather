-- 创建数据库
CREATE DATABASE multiprotgather;

-- 创建用户（如果不存在）
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'multiprotgather_user') THEN

      CREATE ROLE multiprotgather_user LOGIN PASSWORD 'multiprotgather_pass';
   END IF;
END
$do$;

-- 授权
GRANT ALL PRIVILEGES ON DATABASE multiprotgather TO multiprotgather_user;

-- 连接到multiprotgather数据库
\c multiprotgather;

-- 授权schema权限
GRANT ALL ON SCHEMA public TO multiprotgather_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO multiprotgather_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO multiprotgather_user;

-- 设置默认权限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO multiprotgather_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO multiprotgather_user;