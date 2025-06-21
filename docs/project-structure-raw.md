# AI Agent Platform 项目结构

## 项目概述
学校AI Agent平台权限与管理系统，基于Django框架开发。

## 目录结构

```
ai_agent_platform/                    # Django项目根目录
├── manage.py                         # Django管理脚本
├── requirements.txt                  # Python依赖包
├── db.sqlite3                        # SQLite数据库
├── create_demo_data.py              # 演示数据创建脚本
│
├── ai_agent_platform/               # Django主配置目录
│   ├── __init__.py
│   ├── settings.py                  # 项目配置
│   ├── urls.py                      # 主路由配置
│   ├── wsgi.py                      # WSGI配置
│   └── asgi.py                      # ASGI配置
│
├── ai_agent/                        # AI代理核心应用
│   ├── models.py                    # 数据模型（ChatSession, ChatMessage等）
│   ├── views.py                     # 视图控制器
│   ├── services.py                  # AI服务（DeepSeek API集成）
│   ├── urls.py                      # 路由配置
│   ├── admin.py                     # 管理后台配置
│   ├── apps.py                      # 应用配置
│   ├── tests.py                     # 测试用例
│   └── migrations/                  # 数据库迁移文件
│
├── authentication/                  # 用户认证应用
│   ├── models.py                    # 用户模型（CustomUser, LoginLog）
│   ├── views.py                     # 认证视图
│   ├── urls.py                      # 认证路由
│   ├── admin.py                     # 用户管理后台
│   ├── apps.py                      # 应用配置
│   ├── tests.py                     # 测试用例
│   └── migrations/                  # 数据库迁移文件
│
├── behavior_tracking/               # 行为追踪应用
│   ├── models.py                    # 行为记录模型
│   ├── views.py                     # 行为追踪视图
│   ├── urls.py                      # 路由配置
│   ├── admin.py                     # 管理后台
│   ├── apps.py                      # 应用配置
│   ├── tests.py                     # 测试用例
│   └── migrations/                  # 数据库迁移文件
│
├── permissions/                     # 权限管理应用
│   ├── models.py                    # 权限模型
│   ├── views.py                     # 权限管理视图
│   ├── urls.py                      # 路由配置
│   ├── admin.py                     # 管理后台
│   ├── apps.py                      # 应用配置
│   ├── tests.py                     # 测试用例
│   └── migrations/                  # 数据库迁移文件
│
├── student_management/              # 学生管理应用
│   ├── models.py                    # 学生信息模型
│   ├── views.py                     # 学生管理视图
│   ├── urls.py                      # 路由配置
│   ├── admin.py                     # 管理后台
│   ├── apps.py                      # 应用配置
│   ├── tests.py                     # 测试用例
│   └── migrations/                  # 数据库迁移文件
│
├── templates/                       # 前端模板目录
│   ├── base.html                    # 基础模板
│   ├── index.html                   # 首页模板
│   ├── ai_agent/
│   │   └── chat.html               # AI聊天界面
│   └── authentication/
│       └── login.html              # 登录页面
│
├── static/                          # 静态文件目录
│   └── js/                         # JavaScript文件
│
├── media/                           # 用户上传文件目录
│
└── logs/                           # 日志文件目录
    └── django.log                  # Django运行日志
```

## 核心功能模块

### 1. 身份与权限管理 (authentication)
- 用户认证（登录/登出）
- 多角色支持（admin/teacher/student/guest）
- 登录日志记录

### 2. AI代理核心 (ai_agent)
- DeepSeek API集成
- 聊天会话管理
- 消息记录与历史
- 7种AI助手功能

### 3. 行为追踪 (behavior_tracking)
- 用户操作记录
- 交互行为分析

### 4. 权限管理 (permissions)
- 功能权限控制
- 角色权限分配

### 5. 学生管理 (student_management)
- 学生信息管理
- 档案数据维护

## 演示账户
- admin/admin123（管理员）
- teacher/teacher123（教师）
- student/student123（学生）
- guest/guest123（访客）

## 技术栈
- 后端：Django 4.2+
- 前端：Bootstrap 5 + JavaScript
- 数据库：SQLite（开发环境）
- AI服务：DeepSeek API
- 自动化测试：Playwright

## 启动方式
```bash
# 激活虚拟环境
conda activate pywork

# 进入项目目录
cd ai_agent_platform

# 运行开发服务器
python manage.py runserver
```

访问地址：http://127.0.0.1:8000/ 