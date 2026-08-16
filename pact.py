# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json
import datetime


# The three-backtick code fence LLMs wrap JSON in. Built from a char code on
# purpose: this file is embedded inside a JS String.raw template literal in
# index.html, and a literal backtick here would terminate it.
_FENCE = chr(96) * 3


def _pick(d: dict, *names):
    """LLMs rename fields. Accept the aliases they actually reach for."""
    for n in names:
        if n in d and d[n] is not None:
            return d[n]
    return None


def _read_verdict(raw: str) -> tuple:
    """Turn the model's answer into (verdict, reasoning).

    Returns "unfulfilled" whenever the answer cannot be read with confidence.
    Refusing to guess is the safe direction: a pact that wrongly reads as kept
    is far worse than one that asks the parties to look again.
    """
    text = str(raw).replace(_FENCE + "json", "").replace(_FENCE, "").strip()

    verdict = ""
    reasoning = ""

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and start < end:
        try:
            parsed = json.loads(text[start:end + 1])
            if isinstance(parsed, dict):
                verdict = str(_pick(parsed, "verdict", "result", "answer", "decision") or "").strip().lower()
                reasoning = str(_pick(parsed, "reasoning", "reason", "explanation", "why") or "").strip()
        except Exception:
            pass

    # No usable JSON: fall back to reading the bare words out of the text.
    if verdict not in ("fulfilled", "unfulfilled"):
        low = text.lower()
        # "unfulfilled" contains "fulfilled", so it has to be tested first.
        if "unfulfilled" in low or "not fulfilled" in low:
            verdict = "unfulfilled"
        elif "fulfilled" in low:
            verdict = "fulfilled"
        else:
            verdict = "unfulfilled"

    return verdict, reasoning


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

        # Each validator reads the page and judges it independently. Consensus is
        # reached by comparing the two answers, not by demanding identical text:
        # the verdict must agree exactly, while the wording of the reason is free.
        # strict_eq cannot be used here because an LLM never repeats itself word
        # for word, which is why the verdict used to be squeezed into one token.
        def judge() -> str:
            page = gl.nondet.web.render(url, mode="text")

            # An image URL, a login wall or a dead link all render to (almost)
            # nothing. Decide that here rather than asking the model to reason
            # about a blank page, where it is free to invent either answer.
            if len(page.strip()) < 40:
                return json.dumps({
                    "verdict": "unfulfilled",
                    "reasoning": "The evidence page returned no readable text. That happens when the link points at an image file, a page that requires signing in, or a link that no longer resolves. Point it at a public page whose text shows the result.",
                })

            prompt = f"""You are a neutral arbitrator deciding whether a real agreement was kept.

THE AGREEMENT (plain language):
{terms}

WHAT THE EVIDENCE PAGE ACTUALLY CONTAINS:
{page}

Decide, based ONLY on what is actually present on the evidence page, whether the agreement's
requirements were met. Be strict and literal: if the required result is not clearly visible on
the page, it is not fulfilled. Judge the words of the agreement as written, not what you assume
was intended.

Respond using ONLY this JSON format, nothing else:
{{
"verdict": "fulfilled" or "unfulfilled",
"reasoning": "two or three sentences naming the specific thing on the page that decided it, or the specific thing that was missing"
}}
Your output must be only JSON, with no prefix, suffix or code fence, and must parse cleanly."""

            out = gl.nondet.exec_prompt(prompt)
            return str(out).replace(_FENCE + "json", "").replace(_FENCE, "").strip()

        raw = gl.eq_principle.prompt_comparative(
            judge,
            "The value of the verdict field has to match exactly. "
            "The reasoning field only has to reach the same conclusion; "
            "different wording is expected and acceptable.",
        )

        result, reasoning = _read_verdict(raw)

        self.is_settled = True
        if result == "fulfilled":
            self.verdict = "fulfilled"
            self.last_reasoning = reasoning or "The jury read the evidence page and found the agreement's requirements were met."
        else:
            self.verdict = "not_fulfilled"
            self.last_reasoning = reasoning or "The jury read the evidence page but did not find proof the agreement was met. Check that the evidence URL points to exactly where the result should appear."

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
