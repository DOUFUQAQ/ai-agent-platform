"""AI 智能体会话与计量部分的契约测试。

这些用例只依赖数据库与模型定义，不触发任何真实 LLM 调用。
"""
from django.core.management import get_commands
from django.test import TestCase

from ai_agent import models as agent_models
from behavior_tracking import models as behavior_models


class AgentModelContractTests(TestCase):
    def test_expected_models_exist(self):
        for name in ("AIModel", "AIFunction", "APIUsageLog", "UserTokenUsage"):
            with self.subTest(model=name):
                self.assertTrue(hasattr(agent_models, name), "ai_agent.%s 缺失" % name)

    def test_ai_model_tracks_cost_per_1k(self):
        field_names = {f.name for f in agent_models.AIModel._meta.get_fields()}
        self.assertTrue(
            {"cost_per_1k_input_tokens", "cost_per_1k_output_tokens"} <= field_names,
            "AIModel 缺少成本字段: %s" % sorted(field_names),
        )

    def test_user_token_usage_is_daily_and_per_user(self):
        field_names = {f.name for f in agent_models.UserTokenUsage._meta.get_fields()}
        self.assertIn("date", field_names)
        self.assertIn("user", field_names)


class ConversationModelContractTests(TestCase):
    def test_chat_session_and_message_exist(self):
        for name in ("ChatSession", "ChatMessage"):
            with self.subTest(model=name):
                self.assertTrue(
                    hasattr(behavior_models, name),
                    "behavior_tracking.%s 缺失" % name)

    def test_chat_message_records_tokens_and_flags(self):
        field_names = {f.name for f in behavior_models.ChatMessage._meta.get_fields()}
        self.assertIn("tokens_used", field_names)
        self.assertIn("is_flagged", field_names)

    def test_chat_session_uses_started_at(self):
        """历史上 audit_system 曾错用 created_at，这条断言防止回归。"""
        field_names = {f.name for f in behavior_models.ChatSession._meta.get_fields()}
        self.assertIn("started_at", field_names)


class ManagementCommandTests(TestCase):
    def test_token_usage_backfill_command_is_discoverable(self):
        commands = get_commands()
        self.assertIn("update_token_usage", commands)


class MonitoringServiceTests(TestCase):
    def test_sensitive_word_monitor_is_importable(self):
        from behavior_tracking.monitoring import SensitiveWordMonitor

        self.assertTrue(hasattr(SensitiveWordMonitor, "__init__"))

    def test_abnormal_behavior_detector_is_importable(self):
        from behavior_tracking.services import AbnormalBehaviorDetector

        self.assertTrue(hasattr(AbnormalBehaviorDetector, "__init__"))

    def test_sensitive_content_detector_is_importable(self):
        from behavior_tracking.services import SensitiveContentDetector

        self.assertTrue(hasattr(SensitiveContentDetector, "__init__"))
