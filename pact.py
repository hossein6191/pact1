# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json
import datetime


class Pact(gl.Contract):
    party_a: Address
    party_b: Address
    identity_a: str
    identity_b: str
    terms: str
    evidence_url: str
    deadline: u64
    signed_a: bool
    signed_b: bool
    is_active: bool
    is_settled: bool
    verdict: str
    last_reasoning: str
    is_minted: bool
    token_id: str

    def __init__(self, party_b: str, identity_a: str, identity_b: str,
                 terms: str, evidence_url: str, deadline_days: int):
        self.party_a = gl.message.sender_address
        self.party_b = Address(party_b)
        self.identity_a = identity_a
        self.identity_b = identity_b
        self.terms = terms
        self.evidence_url = evidence_url
        self.deadline = self._now() + u64(deadline_days) * u64(86400)
        self.signed_a = True
        self.signed_b = False
        self.is_active = False
        self.is_settled = False
        self.verdict = ""
        self.last_reasoning = ""
        self.is_minted = False
        self.token_id = ""

    def _now(self) -> u64:
        return u64(int(datetime.datetime.now(datetime.timezone.utc).timestamp()))

    def _mint(self) -> None:
        # deterministic token id (no time) so validators always agree
        self.token_id = "PACT-" + self.party_a.as_hex[2:10] + "-" + self.party_b.as_hex[2:10]
        self.is_minted = True

    @gl.public.write
    def sign(self) -> None:
        assert gl.message.sender_address == self.party_b, "Only the counterparty can sign"
        assert not self.signed_b, "You have already signed"
        assert not self.is_settled, "This pact is already settled"
        self.signed_b = True
        if self.signed_a and self.signed_b:
            self.is_active = True
            self._mint()

    @gl.public.write
    def cancel(self) -> None:
        assert not self.is_active, "An active pact cannot be cancelled"
        assert not self.is_settled, "This pact is already settled"
        is_party = (gl.message.sender_address == self.party_a or
                    gl.message.sender_address == self.party_b)
        assert is_party, "Only a party to this pact can cancel it"
        self.is_settled = True
        self.verdict = "cancelled"

    @gl.public.write
    def settle(self) -> str:
        assert self.is_active, "Both parties must sign before judging"
        assert not self.is_settled, "This pact is already settled"
        now = self._now()
        assert now >= self.deadline, "The deadline has not passed yet"

        terms = self.terms
        url = self.evidence_url

        # Only the boolean verdict goes through consensus (strict_eq on a single
        # word), so validators reliably agree. The free-text reason is fetched
        # separately and is allowed to vary.
        def judge_bool() -> str:
            page = gl.nondet.web.render(url, mode="text")
            prompt = f"""You are a neutral arbitrator deciding whether a real agreement was kept.

THE AGREEMENT (plain language):
{terms}

WHAT THE EVIDENCE PAGE ACTUALLY CONTAINS:
{page}

Read the evidence carefully and decide: based ONLY on what is actually present on the evidence page, were the agreement's requirements met?
Be strict and literal. If the required result is not clearly visible on the page, it is not fulfilled.

Answer with ONLY one single lowercase word, nothing else:
fulfilled
or
unfulfilled"""
            out = gl.nondet.exec_prompt(prompt).strip().lower()
            if "unfulfilled" in out:
                return "unfulfilled"
            if "fulfilled" in out:
                return "fulfilled"
            return "unfulfilled"

        result = gl.eq_principle.strict_eq(judge_bool)
        self.is_settled = True
        if result == "fulfilled":
            self.verdict = "fulfilled"
            self.last_reasoning = "The jury read the evidence page and found the agreement's requirements were met."
        else:
            self.verdict = "not_fulfilled"
            self.last_reasoning = "The jury read the evidence page but did not find proof the agreement was met. Check that the evidence URL points to exactly where the result should appear."
        return self.verdict

    @gl.public.view
    def get_status(self) -> str:
        return json.dumps({
            "party_a": self.party_a.as_hex,
            "party_b": self.party_b.as_hex,
            "identity_a": self.identity_a,
            "identity_b": self.identity_b,
            "terms": self.terms,
            "evidence_url": self.evidence_url,
            "deadline": int(self.deadline),
            "signed_a": self.signed_a,
            "signed_b": self.signed_b,
            "is_active": self.is_active,
            "is_settled": self.is_settled,
            "verdict": self.verdict,
            "last_reasoning": self.last_reasoning,
            "is_minted": self.is_minted,
            "token_id": self.token_id,
        })
