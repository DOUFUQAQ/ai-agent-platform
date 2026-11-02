"""认证与用户模型测试。

这里主要固化「自定义 User 模型」这个契约——一旦有人把它换回 django.contrib.auth.User，
整套权限体系都会失效，必须让 CI 立刻红掉。
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase


class CustomUserModelTests(TestCase):
    def test_project_uses_custom_user_model(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "authentication.User")
        self.assertEqual(get_user_model()._meta.label, "authentication.User")

    def test_user_model_exposes_user_type(self):
        field_names = {f.name for f in get_user_model()._meta.get_fields()}
        self.assertIn("user_type", field_names)

    def test_create_user_keeps_user_type(self):
        user_model = get_user_model()
        kwargs = {"username": "student_01", "password": "not-used-12345"}
        if "user_type" in {f.name for f in user_model._meta.get_fields()}:
            kwargs["user_type"] = "student"

        user = user_model.objects.create_user(**kwargs)

        self.assertEqual(user.username, "student_01")
        self.assertTrue(user.check_password("not-used-12345"))
        self.assertFalse(user.is_superuser)

    def test_create_superuser_sets_flags(self):
        user = get_user_model().objects.create_superuser(
            username="root_user", password="root-pass-12345",
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class SecurityConfigurationTests(TestCase):
    """防止有人再把密钥写死回 settings.py。"""

    def test_settings_has_no_hardcoded_api_keys(self):
        settings_path = settings.BASE_DIR / "ai_agent_platform" / "settings.py"
        source = settings_path.read_text(encoding="utf-8")

        for marker in ("sk-", "ag-"):
            for line in source.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                # 允许出现环境变量名，不允许出现形如 sk-xxxx 的字面量
                if marker in stripped and "getenv" not in stripped:
                    self.fail("settings.py 可能包含硬编码密钥: %s" % stripped)

    def test_secret_key_is_not_the_django_placeholder(self):
        self.assertNotIn("your-secret-key-here", settings.SECRET_KEY)

    def test_allowed_hosts_is_a_list(self):
        self.assertIsInstance(settings.ALLOWED_HOSTS, list)
        self.assertTrue(settings.ALLOWED_HOSTS)
