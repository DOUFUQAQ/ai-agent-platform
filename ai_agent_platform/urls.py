"""
AI Agent Platform URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def redirect_to_login(request):
    return redirect('/auth/login/')

urlpatterns = [
    # 管理后台
    path('admin/', admin.site.urls),
    
    # 根路径重定向到登录页
    path('', redirect_to_login),
    
    # 认证模块
    path('auth/', include('authentication.urls')),
    
    # AI代理模块
    path('ai_agent/', include('ai_agent.urls')),
    
    # API接口
    path('api/v1/', include('ai_agent.api_urls')),
    
    # 权限管理模块
    path('permissions/', include('permissions.urls')),
    
    # 行为分析模块
    path('behavior/', include('behavior_tracking.urls')),
    
    # 学生管理模块
    path('students/', include('student_management.urls')),
    
    # 审计系统模块
    path('audit/', include('audit_system.urls')),
]

# 开发环境下的静态文件和媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 自定义admin站点信息
admin.site.site_header = "AI Agent 管理平台"
admin.site.site_title = "AI Agent Admin"
admin.site.index_title = "AI Agent 管理后台"
