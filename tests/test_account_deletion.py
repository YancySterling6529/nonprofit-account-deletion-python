from account_deletion import (
    AccountStore,
    CampaignReportRow,
    DeleteRequest,
    DonorReceipt,
    InfraiClient,
    VolunteerReminder,
    delete_account,
)


class FakeResponse:
    status_code = 200
    headers = {}

    def json(self):
        return {"ok": True, "data": {"score": 0.99}, "error": None, "metadata": {}}


class FakeHttp:
    def post(self, url, **kwargs):
        assert url.endswith("/v1/captcha/verify")
        assert kwargs["json"]["action"] == "account_delete"
        assert kwargs["json"]["widget_record_id"] == "widget-1"
        return FakeResponse()


def test_deletion_revokes_sessions_and_all_domain_records():
    store = AccountStore(
        sessions={"u-1": {"a", "b"}},
        receipts=[DonorReceipt("r", "u-1")],
        reminders=[VolunteerReminder("m", "u-1")],
        report_rows=[CampaignReportRow("c", "u-1")],
    )
    result = delete_account(DeleteRequest("u-1", "token", "127.0.0.1", "widget-1"), store, InfraiClient("test-key", FakeHttp()))
    assert result["sessions_revoked"] == 2
    assert result["records_removed"] == {"receipts": 1, "reminders": 1, "campaign_rows": 1}
    assert not store.sessions and not store.receipts and not store.reminders and not store.report_rows


def test_rate_limit_envelope_retries_before_success(monkeypatch):
    class RateLimited(FakeResponse):
        status_code = 429
        headers = {"Retry-After": "0"}

        def json(self):
            return {"ok": False, "error": {"code": "RATE_LIMITED"}}

    class RetryingHttp(FakeHttp):
        calls = 0

        def post(self, url, **kwargs):
            self.calls += 1
            super().post(url, **kwargs)
            return RateLimited() if self.calls == 1 else FakeResponse()

    monkeypatch.setattr("account_deletion.time.sleep", lambda delay: None)
    http = RetryingHttp()
    assert InfraiClient("test-key", http).verify_captcha("widget-1", "token", "127.0.0.1") == {"score": 0.99}
    assert http.calls == 2
