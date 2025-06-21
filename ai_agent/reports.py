"""
报表导出功能
支持Excel、PDF、CSV等格式的数据导出
"""

import io
import csv
import json
from datetime import datetime, timedelta
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count, Q, Avg, Sum
from django.contrib.auth import get_user_model
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import LineChart, BarChart, PieChart, Reference
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie

from behavior_tracking.models import ChatSession, ChatMessage, SensitiveWordDetection, AbnormalBehaviorDetection
from permissions.models import AIFunction, StudentFunctionPermission
from student_management.models import StudentUsageStatistics, StudentTag

User = get_user_model()


class ReportGenerator:
    """报表生成器基类"""
    
    def __init__(self, start_date=None, end_date=None):
        self.start_date = start_date or (timezone.now() - timedelta(days=30)).date()
        self.end_date = end_date or timezone.now().date()
    
    def get_base_queryset(self, model, date_field='created_at'):
        """获取基础查询集"""
        return model.objects.filter(
            **{f'{date_field}__date__gte': self.start_date,
               f'{date_field}__date__lte': self.end_date}
        )


class UserActivityReportGenerator(ReportGenerator):
    """用户活动报表生成器"""
    
    def get_data(self):
        """获取用户活动数据"""
        # 用户统计
        total_users = User.objects.filter(user_type='student').count()
        active_users = ChatSession.objects.filter(
            started_at__date__gte=self.start_date,
            started_at__date__lte=self.end_date
        ).values('user').distinct().count()
        
        # 会话统计
        sessions = self.get_base_queryset(ChatSession, 'started_at')
        total_sessions = sessions.count()
        avg_session_duration = sessions.filter(
            ended_at__isnull=False
        ).aggregate(
            avg_duration=Avg('ended_at__timestamp') - Avg('started_at__timestamp')
        )['avg_duration'] or 0
        
        # 消息统计
        messages = self.get_base_queryset(ChatMessage)
        total_messages = messages.count()
        avg_messages_per_session = total_messages / total_sessions if total_sessions > 0 else 0
        
        # 每日活跃用户数据
        daily_data = []
        current_date = self.start_date
        while current_date <= self.end_date:
            daily_active = ChatSession.objects.filter(
                started_at__date=current_date
            ).values('user').distinct().count()
            
            daily_sessions = ChatSession.objects.filter(
                started_at__date=current_date
            ).count()
            
            daily_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'active_users': daily_active,
                'sessions': daily_sessions
            })
            current_date += timedelta(days=1)
        
        # 功能使用统计
        function_usage = messages.filter(
            function_called__isnull=False
        ).values('function_called').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return {
            'summary': {
                'total_users': total_users,
                'active_users': active_users,
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'avg_session_duration_minutes': round(avg_session_duration / 60, 2),
                'avg_messages_per_session': round(avg_messages_per_session, 2)
            },
            'daily_data': daily_data,
            'function_usage': list(function_usage)
        }
    
    def export_excel(self):
        """导出Excel报表"""
        data = self.get_data()
        
        # 创建工作簿
        wb = Workbook()
        ws = wb.active
        ws.title = "用户活动报表"
        
        # 设置样式
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        
        # 报表标题
        ws.merge_cells('A1:F1')
        ws['A1'] = f"用户活动报表 ({self.start_date} 至 {self.end_date})"
        ws['A1'].font = Font(size=16, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        # 汇总信息
        ws['A3'] = "汇总信息"
        ws['A3'].font = header_font
        ws['A3'].fill = header_fill
        
        summary_data = [
            ['总用户数', data['summary']['total_users']],
            ['活跃用户数', data['summary']['active_users']],
            ['总会话数', data['summary']['total_sessions']],
            ['总消息数', data['summary']['total_messages']],
            ['平均会话时长(分钟)', data['summary']['avg_session_duration_minutes']],
            ['平均每会话消息数', data['summary']['avg_messages_per_session']]
        ]
        
        for i, (label, value) in enumerate(summary_data, start=4):
            ws[f'A{i}'] = label
            ws[f'B{i}'] = value
        
        # 每日数据
        start_row = len(summary_data) + 6
        ws[f'A{start_row}'] = "每日活跃度"
        ws[f'A{start_row}'].font = header_font
        ws[f'A{start_row}'].fill = header_fill
        
        # 表头
        headers = ['日期', '活跃用户数', '会话数']
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=start_row + 1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
        
        # 数据行
        for i, day_data in enumerate(data['daily_data'], start=start_row + 2):
            ws[f'A{i}'] = day_data['date']
            ws[f'B{i}'] = day_data['active_users']
            ws[f'C{i}'] = day_data['sessions']
        
        # 创建图表
        chart = LineChart()
        chart.title = "每日活跃用户趋势"
        chart.style = 13
        chart.x_axis.title = '日期'
        chart.y_axis.title = '用户数'
        
        data_range = Reference(ws, min_col=2, min_row=start_row + 1, 
                              max_col=2, max_row=start_row + 1 + len(data['daily_data']))
        cats = Reference(ws, min_col=1, min_row=start_row + 2, 
                        max_row=start_row + 1 + len(data['daily_data']))
        
        chart.add_data(data_range, titles_from_data=True)
        chart.set_categories(cats)
        
        ws.add_chart(chart, "E3")
        
        # 功能使用统计
        func_start_row = start_row + len(data['daily_data']) + 4
        ws[f'A{func_start_row}'] = "功能使用统计"
        ws[f'A{func_start_row}'].font = header_font
        ws[f'A{func_start_row}'].fill = header_fill
        
        func_headers = ['功能代码', '使用次数']
        for col, header in enumerate(func_headers, start=1):
            cell = ws.cell(row=func_start_row + 1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
        
        for i, func_data in enumerate(data['function_usage'], start=func_start_row + 2):
            ws[f'A{i}'] = func_data['function_called']
            ws[f'B{i}'] = func_data['count']
        
        # 保存到内存
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return output
    
    def export_csv(self):
        """导出CSV报表"""
        data = self.get_data()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入汇总信息
        writer.writerow([f'用户活动报表 ({self.start_date} 至 {self.end_date})'])
        writer.writerow([])
        writer.writerow(['汇总信息'])
        writer.writerow(['指标', '数值'])
        
        for key, value in data['summary'].items():
            writer.writerow([key, value])
        
        writer.writerow([])
        writer.writerow(['每日活跃度'])
        writer.writerow(['日期', '活跃用户数', '会话数'])
        
        for day_data in data['daily_data']:
            writer.writerow([day_data['date'], day_data['active_users'], day_data['sessions']])
        
        writer.writerow([])
        writer.writerow(['功能使用统计'])
        writer.writerow(['功能代码', '使用次数'])
        
        for func_data in data['function_usage']:
            writer.writerow([func_data['function_called'], func_data['count']])
        
        output.seek(0)
        return output


class SecurityReportGenerator(ReportGenerator):
    """安全报表生成器"""
    
    def get_data(self):
        """获取安全数据"""
        # 敏感词检测统计
        sensitive_detections = self.get_base_queryset(SensitiveWordDetection)
        total_sensitive = sensitive_detections.count()
        
        sensitive_by_type = sensitive_detections.values('detection_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        sensitive_by_severity = sensitive_detections.values('severity').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 异常行为检测统计
        abnormal_detections = self.get_base_queryset(AbnormalBehaviorDetection)
        total_abnormal = abnormal_detections.count()
        
        abnormal_by_type = abnormal_detections.values('behavior_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 高风险用户
        high_risk_users = abnormal_detections.filter(
            risk_score__gte=80
        ).values('user__username').annotate(
            count=Count('id'),
            avg_risk=Avg('risk_score')
        ).order_by('-count')
        
        # 每日安全事件
        daily_security = []
        current_date = self.start_date
        while current_date <= self.end_date:
            daily_sensitive = SensitiveWordDetection.objects.filter(
                created_at__date=current_date
            ).count()
            
            daily_abnormal = AbnormalBehaviorDetection.objects.filter(
                created_at__date=current_date
            ).count()
            
            daily_security.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'sensitive_count': daily_sensitive,
                'abnormal_count': daily_abnormal
            })
            current_date += timedelta(days=1)
        
        return {
            'summary': {
                'total_sensitive': total_sensitive,
                'total_abnormal': total_abnormal,
                'total_security_events': total_sensitive + total_abnormal
            },
            'sensitive_by_type': list(sensitive_by_type),
            'sensitive_by_severity': list(sensitive_by_severity),
            'abnormal_by_type': list(abnormal_by_type),
            'high_risk_users': list(high_risk_users),
            'daily_security': daily_security
        }
    
    def export_excel(self):
        """导出安全报表Excel"""
        data = self.get_data()
        
        wb = Workbook()
        ws = wb.active
        ws.title = "安全报表"
        
        # 设置样式
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="DC3545", end_color="DC3545", fill_type="solid")
        
        # 报表标题
        ws.merge_cells('A1:F1')
        ws['A1'] = f"安全报表 ({self.start_date} 至 {self.end_date})"
        ws['A1'].font = Font(size=16, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        # 汇总信息
        ws['A3'] = "安全事件汇总"
        ws['A3'].font = header_font
        ws['A3'].fill = header_fill
        
        summary_data = [
            ['敏感词检测', data['summary']['total_sensitive']],
            ['异常行为检测', data['summary']['total_abnormal']],
            ['总安全事件', data['summary']['total_security_events']]
        ]
        
        for i, (label, value) in enumerate(summary_data, start=4):
            ws[f'A{i}'] = label
            ws[f'B{i}'] = value
        
        # 敏感词类型分布
        current_row = 8
        ws[f'A{current_row}'] = "敏感词类型分布"
        ws[f'A{current_row}'].font = header_font
        ws[f'A{current_row}'].fill = header_fill
        
        for i, item in enumerate(data['sensitive_by_type'], start=current_row + 1):
            ws[f'A{i}'] = item['detection_type']
            ws[f'B{i}'] = item['count']
        
        # 高风险用户
        risk_start_row = current_row + len(data['sensitive_by_type']) + 3
        ws[f'A{risk_start_row}'] = "高风险用户"
        ws[f'A{risk_start_row}'].font = header_font
        ws[f'A{risk_start_row}'].fill = header_fill
        
        risk_headers = ['用户名', '异常次数', '平均风险分']
        for col, header in enumerate(risk_headers, start=1):
            cell = ws.cell(row=risk_start_row + 1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
        
        for i, user_data in enumerate(data['high_risk_users'], start=risk_start_row + 2):
            ws[f'A{i}'] = user_data['user__username']
            ws[f'B{i}'] = user_data['count']
            ws[f'C{i}'] = round(user_data['avg_risk'], 2)
        
        # 保存到内存
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return output


class UsageStatisticsReportGenerator(ReportGenerator):
    """使用统计报表生成器"""
    
    def get_data(self):
        """获取使用统计数据"""
        # 总体统计
        usage_stats = self.get_base_queryset(StudentUsageStatistics, 'date')
        
        total_usage = usage_stats.aggregate(
            total_sessions=Sum('total_sessions'),
            total_messages=Sum('total_messages'),
            total_duration=Sum('total_duration_minutes')
        )
        
        # 按用户统计
        user_stats = usage_stats.values('student__username').annotate(
            total_sessions=Sum('total_sessions'),
            total_messages=Sum('total_messages'),
            total_duration=Sum('total_duration_minutes')
        ).order_by('-total_sessions')
        
        # 按日期统计
        daily_stats = usage_stats.values('date').annotate(
            total_sessions=Sum('total_sessions'),
            total_messages=Sum('total_messages'),
            total_duration=Sum('total_duration_minutes')
        ).order_by('date')
        
        # 功能使用分析
        function_analysis = ChatMessage.objects.filter(
            created_at__date__gte=self.start_date,
            created_at__date__lte=self.end_date,
            function_called__isnull=False
        ).values('function_called').annotate(
            count=Count('id'),
            unique_users=Count('session__user', distinct=True)
        ).order_by('-count')
        
        return {
            'summary': total_usage,
            'user_stats': list(user_stats),
            'daily_stats': list(daily_stats),
            'function_analysis': list(function_analysis)
        }
    
    def export_excel(self):
        """导出使用统计Excel报表"""
        data = self.get_data()
        
        wb = Workbook()
        ws = wb.active
        ws.title = "使用统计报表"
        
        # 设置样式
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="28A745", end_color="28A745", fill_type="solid")
        
        # 报表标题
        ws.merge_cells('A1:F1')
        ws['A1'] = f"使用统计报表 ({self.start_date} 至 {self.end_date})"
        ws['A1'].font = Font(size=16, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        # 总体统计
        ws['A3'] = "总体统计"
        ws['A3'].font = header_font
        ws['A3'].fill = header_fill
        
        summary_data = [
            ['总会话数', data['summary']['total_sessions'] or 0],
            ['总消息数', data['summary']['total_messages'] or 0],
            ['总使用时长(分钟)', data['summary']['total_duration'] or 0]
        ]
        
        for i, (label, value) in enumerate(summary_data, start=4):
            ws[f'A{i}'] = label
            ws[f'B{i}'] = value
        
        # 用户统计
        user_start_row = 8
        ws[f'A{user_start_row}'] = "用户使用统计"
        ws[f'A{user_start_row}'].font = header_font
        ws[f'A{user_start_row}'].fill = header_fill
        
        user_headers = ['用户名', '总会话数', '总消息数', '总时长(分钟)']
        for col, header in enumerate(user_headers, start=1):
            cell = ws.cell(row=user_start_row + 1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
        
        for i, user_data in enumerate(data['user_stats'], start=user_start_row + 2):
            ws[f'A{i}'] = user_data['student__username']
            ws[f'B{i}'] = user_data['total_sessions'] or 0
            ws[f'C{i}'] = user_data['total_messages'] or 0
            ws[f'D{i}'] = user_data['total_duration'] or 0
        
        # 保存到内存
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return output


def export_user_activity_report(request, format='excel'):
    """导出用户活动报表"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    generator = UserActivityReportGenerator(start_date, end_date)
    
    if format == 'excel':
        output = generator.export_excel()
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="user_activity_report_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    elif format == 'csv':
        output = generator.export_csv()
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="user_activity_report_{timezone.now().strftime("%Y%m%d")}.csv"'
    else:
        return HttpResponse("不支持的格式", status=400)
    
    return response


def export_security_report(request, format='excel'):
    """导出安全报表"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    generator = SecurityReportGenerator(start_date, end_date)
    output = generator.export_excel()
    
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="security_report_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    
    return response


def export_usage_statistics_report(request, format='excel'):
    """导出使用统计报表"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    generator = UsageStatisticsReportGenerator(start_date, end_date)
    output = generator.export_excel()
    
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="usage_statistics_report_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    
    return response 