"""Smoke and regression tests for the health_checks app.

These exercise the pages and flows that were previously broken (missing
templates, bad URL names, and the participate-session save bug) so the same
regressions cannot slip back in.
"""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from departments.models import Department
from teams.models import Team
from health_checks.models import (
    HealthCheck, HealthCheckCategory, HealthCheckQuestion,
    HealthCheckSession, HealthCheckResponse,
)


class HealthCheckPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="admin", email="admin@example.com", password="pass1234",
            role=User.ADMIN, is_staff=True, is_superuser=True,
        )
        cls.dept = Department.objects.create(name="Engineering")
        cls.team = Team.objects.create(name="Alpha", department=cls.dept)
        cls.team.add_member(cls.admin, is_leader=True)
        cls.hc = HealthCheck.objects.create(name="Q1 Check", created_by=cls.admin)
        cls.cat = HealthCheckCategory.objects.create(name="Delivery", order=1)
        cls.q = HealthCheckQuestion.objects.create(text="Do we ship?", category=cls.cat)
        cls.session = HealthCheckSession.objects.create(
            health_check=cls.hc, team=cls.team,
            end_date=timezone.now() + timedelta(days=7), created_by=cls.admin,
        )
        cls.session.participants.add(cls.admin)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_pages_load(self):
        """Every previously-broken page now returns 200."""
        names = [
            ("session_list", []),
            ("category_list", []),
            ("create_category", []),
            ("edit_category", [self.cat.id]),
            ("question_list", []),
            ("create_question", []),
            ("edit_question", [self.q.id]),
            ("participate_session", [self.session.id]),
            ("session_results", [self.session.id]),
            ("delete_health_check", [self.hc.id]),
        ]
        for name, args in names:
            with self.subTest(view=name):
                resp = self.client.get(reverse(name, args=args))
                self.assertEqual(resp.status_code, 200)

    def test_session_is_active_property(self):
        self.assertTrue(self.session.is_active)
        self.assertFalse(self.session.is_past)
        self.assertFalse(self.session.is_upcoming)

    def test_participate_saves_response(self):
        """Submitting the participate formset stores a response (regression)."""
        url = reverse("participate_session", args=[self.session.id])
        data = {
            "form-TOTAL_FORMS": "1", "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0", "form-MAX_NUM_FORMS": "1000",
            "form-0-question": self.q.id, "form-0-status": "doing_well",
            "form-0-comment": "All good",
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            HealthCheckResponse.objects.filter(
                session=self.session, question=self.q, user=self.admin
            ).count(), 1,
        )

    def test_create_category(self):
        resp = self.client.post(
            reverse("create_category"),
            {"name": "Teamwork", "description": "", "order": 2},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(HealthCheckCategory.objects.filter(name="Teamwork").exists())
