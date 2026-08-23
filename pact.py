# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json
import hashlib
import datetime

# The three-backtick code fence LLMs wrap JSON in. Built from a char code on
# purpose: this file is embedded inside a JS String.raw template literal in
# index.html, and a literal backtick here would terminate it.
_FENCE = chr(96) * 3

# Paying an ordinary wallet is an external message to the chain layer, which is
# reached through the EVM interface even though the recipient is not a contract.
@gl.evm.contract_interface
class _Payee:
    class View:
        pass

    class Write:
        pass


_HEX = "0123456789abcdef"
_RAW = "https://raw.githubusercontent.com/"


def _is_commit_hash(s: str) -> bool:
    if len(s) != 40:
        return False
    low = s.lower()
    for ch in low:
        if ch not in _HEX:
            return False
    return True


def _pin_error(url: str) -> str:
    """Empty string if the URL names an immutable artifact, else why it does not.

    A git commit hash is a hash over the exact tree it points at, so bytes served
    for that hash cannot be swapped later without the hash changing. A branch name
    points at whatever the branch holds today, which is the hole this closes.
    """
    u = url.strip()
    if not u.startswith(_RAW):
        return ("Evidence has to be a commit pinned GitHub raw file, so it must start "
                "with " + _RAW + " . Anything else can be edited after both parties sign.")
    parts = u[len(_RAW):].split("/")
    if len(parts) < 4:
        return "The link is missing the owner, the repository, the commit hash or the file path."
    if not _is_commit_hash(parts[2]):
        return ("The third segment has to be a full 40 character commit hash, not '"
                + parts[2] + "'. A branch name can be rewritten after signing.")
    if parts[3] == "":
        return "The link carries a commit hash but no file path after it."
    return ""


_IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg")


def _is_image(url: str) -> bool:
    low = url.strip().lower()
    for e in _IMG_EXT:
        if low.endswith(e):
            return True
    return False


def _commit_of(url: str) -> str:
    """The commit hash out of an already validated pinned URL."""
    parts = url.strip()[len(_RAW):].split("/")
    if len(parts) >= 3:
        return parts[2].lower()
    return ""


def _pick(d: dict, *names):
    """LLMs rename fields. Accept the aliases they actually reach for."""
    for n in names:
        if n in d and d[n] is not None:
            return d[n]
    return None


def _read_verdict(raw) -> tuple:
    """Turn the model's answer (a dict in JSON mode, or any text) into
    (verdict, reasoning).

    Returns "unfulfilled" whenever the answer cannot be read with confidence.
    Refusing to guess is the safe direction: a pact that wrongly reads as kept
    is far worse than one that asks the parties to look again.
    """
    verdict = ""
    reasoning = ""
    parsed = raw if isinstance(raw, dict) else None
    text = "" if isinstance(raw, dict) else str(raw).replace(_FENCE + "json", "").replace(_FENCE, "").strip()

    if parsed is None:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and start < end:
            try:
                cand = json.loads(text[start:end + 1])
                if isinstance(cand, dict):
                    parsed = cand
            except Exception:
                parsed = None
    if isinstance(parsed, dict):
        verdict = str(_pick(parsed, "verdict", "result", "answer", "decision") or "").strip().lower()
        reasoning = str(_pick(parsed, "reasoning", "reason", "explanation", "why") or "").strip()

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
    deadline: u64
    signed_a: bool
    signed_b: bool
    is_active: bool
    is_settled: bool
    verdict: str
    last_reasoning: str
    is_minted: bool
    token_id: str
    evidence_url: str
    evidence_by: str
    evidence_at: u64
    evidence_digest: str
    escrow: u256
    paid_to: str

    def __init__(self, party_b: str, identity_a: str, identity_b: str,
                 terms: str, deadline_seconds: int):
        self.party_a = gl.message.sender_address
        self.party_b = Address(party_b)
        self.identity_a = identity_a
        self.identity_b = identity_b
        self.terms = terms
        self.deadline = self._now() + u64(deadline_seconds)
        self.signed_a = True
        self.signed_b = False
        self.is_active = False
        self.is_settled = False
        self.verdict = ""
        self.last_reasoning = ""
        self.is_minted = False
        self.token_id = ""
        self.evidence_url = ""
        self.evidence_by = ""
        self.evidence_at = u64(0)
        self.evidence_digest = ""
        self.escrow = u256(0)
        self.paid_to = ""

    def _now(self) -> u64:
        return u64(int(datetime.datetime.now(datetime.timezone.utc).timestamp()))

    def _mint(self) -> None:
        # deterministic token id (no time) so validators always agree
        self.token_id = "PACT-" + self.party_a.as_hex[2:10] + "-" + self.party_b.as_hex[2:10]
        self.is_minted = True

    def _release(self, to: Address) -> None:
        """Move the whole escrow once, and never leave it stranded.

        Every path that ends a pact calls this, so the money always has somewhere
        to go. The balance is zeroed before the transfer is queued: the transfer
        itself lands when this transaction finalizes, not when it is accepted.
        """
        amount = self.escrow
        if amount == u256(0):
            return
        self.escrow = u256(0)
        self.paid_to = to.as_hex
        _Payee(to).emit_transfer(value=amount)

    @gl.public.write.payable
    def fund(self) -> None:
        assert gl.message.sender_address == self.party_a, "Only the party who drafted this pact can fund it"
        assert not self.is_settled, "This pact is already settled"
        v = gl.message.value
        assert v > u256(0), "Send an amount greater than zero"
        self.escrow = self.escrow + v

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
    def submit_evidence(self, url: str) -> None:
        """The obligated party files their own proof, on chain, before the deadline.

        This is the half the drafter used to control. Now the side that owes the
        work names the artifact, signs that act with their own wallet, and does it
        inside a window both parties agreed to. It can be replaced while the window
        is open, so a wrong link is fixable, and it is frozen the moment it closes.
        """
        assert self.is_active, "Both parties must sign before evidence can be filed"
        assert not self.is_settled, "This pact is already settled"
        assert gl.message.sender_address == self.party_b, "Only the obligated party can file evidence"
        assert self._now() < self.deadline, "The deadline has passed, evidence is closed"
        problem = _pin_error(url)
        assert problem == "", problem
        self.evidence_url = url.strip()
        self.evidence_by = gl.message.sender_address.as_hex
        self.evidence_at = self._now()

    @gl.public.write
    def cancel(self) -> None:
        assert not self.is_active, "An active pact cannot be cancelled"
        assert not self.is_settled, "This pact is already settled"
        is_party = (gl.message.sender_address == self.party_a or
                    gl.message.sender_address == self.party_b)
        assert is_party, "Only a party to this pact can cancel it"
        self.is_settled = True
        self.verdict = "cancelled"
        self.last_reasoning = "Cancelled before it went live. Anything funded returns to the party who funded it."
        self._release(self.party_a)

    @gl.public.write
    def settle(self) -> str:
        assert self.is_active, "Both parties must sign before judging"
        assert not self.is_settled, "This pact is already settled"
        assert self._now() >= self.deadline, "The deadline has not passed yet"

        # Nothing was ever filed. Close it without asking a model to reason about
        # an absence, and send the money back.
        if self.evidence_url == "":
            self.is_settled = True
            self.verdict = "not_fulfilled"
            self.last_reasoning = ("No evidence was filed before the deadline closed. There is "
                                   "nothing to read, so the pact closes unfulfilled and anything "
                                   "escrowed returns to the party who funded it.")
            self._release(self.party_a)
            return self.verdict

        url = self.evidence_url
        terms = self.terms

        # An image has no text for validators to agree on, so the two halves of the
        # guarantee split: the commit hash fixes the bytes, and the jury looks at the
        # picture. The answer is held to a tight shape on purpose. Left free the models
        # write a paragraph of thinking each, the paragraphs never match, and consensus
        # fails on wording rather than on what anyone actually saw.
        if _is_image(url):
            self.evidence_digest = "git-commit:" + _commit_of(url)

            # Leader and validators each look at the picture themselves. The
            # validator agrees only if its own verdict word is the leader's: the
            # leader's answer is never authoritative, and the reasoning text is
            # left free because two honest readers never phrase it identically.
            def leader_fn():
                def look():
                    shot = gl.nondet.web.render(url, mode="screenshot")
                    prompt = ("You are a neutral arbitrator deciding whether a delivered image meets an agreement.\n\n"
                              "THE AGREEMENT:\n" + terms + "\n\n"
                              "You are looking at the delivered image itself. Judge only what is visibly there. "
                              "Do not judge taste, quality or effort.\n\n"
                              "Respond with ONLY this JSON and nothing else. No preamble, no reasoning out loud, no code fence:\n"
                              '{"verdict": "fulfilled" or "unfulfilled", "reasoning": "at most 12 words naming what you actually see"}')
                    out = gl.nondet.exec_prompt(prompt, images=[shot], response_format="json")
                    v, why = _read_verdict(out)
                    return {"verdict": v, "reasoning": why}
                return look()

            def validator_fn(leaders_res) -> bool:
                if not isinstance(leaders_res, gl.vm.Return):
                    return False
                try:
                    mine = leader_fn()
                    return str(mine.get("verdict")) == str(leaders_res.calldata.get("verdict"))
                except Exception:
                    return False

            judged = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
            result = str(judged.get("verdict", "unfulfilled"))
            reasoning = str(judged.get("reasoning", ""))
            self.is_settled = True
            if result == "fulfilled":
                self.verdict = "fulfilled"
                self.last_reasoning = reasoning or "The jury looked at the delivered image and found it met the agreement."
                self._release(self.party_b)
            else:
                self.verdict = "not_fulfilled"
                self.last_reasoning = reasoning or "The jury looked at the delivered image and did not find what the agreement asked for."
                self._release(self.party_a)
            return self.verdict

        # Step one is deterministic on purpose. Every validator has to come back
        # with byte identical content before anyone is asked to judge it, and the
        # hash of exactly what was judged is written on chain so a reader can fetch
        # the same pinned artifact and confirm they are looking at the same bytes.
        def grab() -> str:
            return gl.nondet.web.render(url, mode="text")

        page = gl.eq_principle.strict_eq(grab)
        digest = hashlib.sha256(page.encode("utf-8")).hexdigest()
        self.evidence_digest = digest

        if len(page.strip()) < 40:
            self.is_settled = True
            self.verdict = "not_fulfilled"
            self.last_reasoning = ("The pinned artifact came back empty or missing, which happens "
                                   "when the commit or the path is wrong. There was nothing to "
                                   "judge, so the escrow returns to the party who funded it.")
            self._release(self.party_a)
            return self.verdict

        # Step two is the judgment, and it runs over the content the validators
        # already agreed on rather than over whatever each of them happened to
        # fetch. Leader and validators each ask the model; the validator agrees
        # only if its own verdict word is the leader's. The reasoning is free.
        def leader_fn():
            def judge():
                prompt = f"""You are a neutral arbitrator deciding whether a real agreement was kept.

THE AGREEMENT (plain language):
{terms}

THE EVIDENCE ARTIFACT (fixed at commit {url}, identical for every validator):
{page}

Decide, based ONLY on what is actually present in the artifact above, whether the agreement's
requirements were met. Be strict and literal: if the required thing is not clearly present,
it is not fulfilled. Judge the words of the agreement as written, not what you assume was
intended.

Respond using ONLY this JSON format, nothing else:
{{
"verdict": "fulfilled" or "unfulfilled",
"reasoning": "two or three sentences naming the specific thing in the artifact that decided it, or the specific thing that was missing"
}}
Your output must be only JSON, with no prefix, suffix or code fence, and must parse cleanly."""
                out = gl.nondet.exec_prompt(prompt, response_format="json")
                v, why = _read_verdict(out)
                return {"verdict": v, "reasoning": why}
            return judge()

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            try:
                mine = leader_fn()
                return str(mine.get("verdict")) == str(leaders_res.calldata.get("verdict"))
            except Exception:
                return False

        judged = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        result = str(judged.get("verdict", "unfulfilled"))
        reasoning = str(judged.get("reasoning", ""))


        self.is_settled = True
        if result == "fulfilled":
            self.verdict = "fulfilled"
            self.last_reasoning = reasoning or "The jury read the pinned artifact and found the agreement's requirements were met."
            self._release(self.party_b)
        else:
            self.verdict = "not_fulfilled"
            self.last_reasoning = reasoning or "The jury read the pinned artifact but did not find proof the agreement was met."
            self._release(self.party_a)

        return self.verdict

    @gl.public.view
    def get_status(self) -> str:
        return json.dumps({
            "party_a": self.party_a.as_hex,
            "party_b": self.party_b.as_hex,
            "identity_a": self.identity_a,
            "identity_b": self.identity_b,
            "terms": self.terms,
            "deadline": int(self.deadline),
            "signed_a": self.signed_a,
            "signed_b": self.signed_b,
            "is_active": self.is_active,
            "is_settled": self.is_settled,
            "verdict": self.verdict,
            "last_reasoning": self.last_reasoning,
            "is_minted": self.is_minted,
            "token_id": self.token_id,
            "evidence_url": self.evidence_url,
            "evidence_by": self.evidence_by,
            "evidence_at": int(self.evidence_at),
            "evidence_digest": self.evidence_digest,
            "escrow": str(int(self.escrow)),
            "paid_to": self.paid_to,
        })
