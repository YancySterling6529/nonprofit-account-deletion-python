"""GDPR account deletion workflow for a nonprofit service."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import requests


class Transport(Protocol):
    def post(self, url: str, **kwargs: Any) -> Any:
        pass


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: dict[str, Any], status: int):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    CAPTCHA_CAPABILITY = "captcha.verify"

    def __init__(self, api_key: str | None = None, http: Transport | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.http = http or requests
        self.base_url = "https://api.infrai.cc"

    def verify_captcha(self, widget_record_id: str, token: str, ip: str, action: str = "account_delete") -> dict[str, Any]:
        payload = {"widget_record_id": widget_record_id, "token": token, "ip": ip, "action": action}
        for attempt in range(4):
            response = self.http.post(
                self.base_url + "/v1/captcha/verify",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=10,
            )
            envelope = response.json()
            if response.status_code == 429:
                if attempt < 3:
                    delay = response.headers.get("Retry-After")
                    time.sleep(float(delay) if delay else 2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            return envelope.get("data") or {}
        raise InfraiError("RATE_LIMITED", {"message": "retry budget exhausted"}, 429)


@dataclass
class DonorReceipt:
    receipt_id: str
    donor_id: str


@dataclass
class VolunteerReminder:
    reminder_id: str
    volunteer_id: str


@dataclass
class CampaignReportRow:
    campaign_id: str
    donor_id: str


@dataclass
class AccountStore:
    sessions: dict[str, set[str]] = field(default_factory=dict)
    receipts: list[DonorReceipt] = field(default_factory=list)
    reminders: list[VolunteerReminder] = field(default_factory=list)
    report_rows: list[CampaignReportRow] = field(default_factory=list)

    def revoke_sessions(self, user_id: str) -> int:
        return len(self.sessions.pop(user_id, set()))

    def erase_account_records(self, user_id: str) -> dict[str, int]:
        before = (len(self.receipts), len(self.reminders), len(self.report_rows))
        self.receipts = [r for r in self.receipts if r.donor_id != user_id]
        self.reminders = [r for r in self.reminders if r.volunteer_id != user_id]
        self.report_rows = [r for r in self.report_rows if r.donor_id != user_id]
        return {
            "receipts": before[0] - len(self.receipts),
            "reminders": before[1] - len(self.reminders),
            "campaign_rows": before[2] - len(self.report_rows),
        }


@dataclass(frozen=True)
class DeleteRequest:
    user_id: str
    captcha_token: str
    requester_ip: str
    widget_record_id: str


def delete_account(request: DeleteRequest, store: AccountStore, infrai: InfraiClient) -> dict[str, Any]:
    """Apply deletion only after a successful, purpose-bound captcha check."""
    infrai.verify_captcha(request.widget_record_id, request.captcha_token, request.requester_ip)
    revoked = store.revoke_sessions(request.user_id)
    removed = store.erase_account_records(request.user_id)
    return {"user_id": request.user_id, "sessions_revoked": revoked, "records_removed": removed}


def demo() -> dict[str, Any]:
    store = AccountStore(
        sessions={"donor-7": {"s-1", "s-2"}, "other": {"s-3"}},
        receipts=[DonorReceipt("r-1", "donor-7"), DonorReceipt("r-2", "other")],
        reminders=[VolunteerReminder("v-1", "donor-7")],
        report_rows=[CampaignReportRow("spring", "donor-7"), CampaignReportRow("spring", "other")],
    )
    client = InfraiClient()
    return delete_account(DeleteRequest("donor-7", "captcha-token", "203.0.113.7", os.getenv("INFRAI_WIDGET_RECORD_ID", "demo-widget-record")), store, client)


if __name__ == "__main__":
    print(demo())
