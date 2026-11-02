"""权限模型契约测试。

权限体系是这个平台的治理核心，字段一旦漂移（历史上真发生过：两个 app 各定义了一个
字段名不同的 AIFunction），所有权限判断都会静默失效。这里把关键契约固化下来。
"""
from django.test import TestCase

from permissions import models as permissions_models


class PermissionModelContractTests(TestCase):
    def test_expected_models_exist(self):
        expected = [
            "AIFunction",
            "StudentGroup",
            "StudentFunctionPermission",
            "GroupFunctionPermission",
            "FunctionToggleLog",
            "GrayReleaseConfig",
            "PermissionAuditLog",
        ]
        for name in expected:
            with self.subTest(model=name):
                self.assertTrue(
                    hasattr(permissions_models, name),
                    "permissions.%s 缺失" % name,
                )

    def test_ai_function_uses_function_code(self):
        field_names = {f.name for f in permissions_models.AIFunction._meta.get_fields()}
        self.assertIn("function_code", field_names)
        # 提醒：ai_agent.AIFunction 用的是 code，两者不一致（见 README「已知问题」）
        self.assertNotIn("code", field_names)

    def test_gray_release_config_links_groups(self):
        field_names = {f.name for f in permissions_models.GrayReleaseConfig._meta.get_fields()}
        # 灰度发布靠「目标分组 + 白名单用户」两层命中
        self.assertIn("target_groups", field_names)
        self.assertIn("whitelist_users", field_names)
        self.assertIn("target_percentage", field_names)

    def test_toggle_log_records_old_and_new_values(self):
        field_names = {f.name for f in permissions_models.FunctionToggleLog._meta.get_fields()}
        self.assertIn("old_value", field_names)
        self.assertIn("new_value", field_names)


class FunctionToggleServiceTests(TestCase):
    def test_service_is_importable(self):
        from permissions.function_toggle_service import FunctionToggleService

        self.assertTrue(hasattr(FunctionToggleService, "__init__"))

    def test_decorators_module_exposes_permission_helper(self):
        from permissions import decorators

        public = [name for name in dir(decorators) if not name.startswith("_")]
        self.assertTrue(public, "permissions.decorators 应当导出权限装饰器")
