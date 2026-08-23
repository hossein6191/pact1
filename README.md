# Pact — Agreements the Internet Can Judge

**Two people write a deal in plain words, both sign it with their own wallets, one of them locks up an amount, and after the deadline a jury of AI validators reads the filed evidence and decides who the money goes to.**

**Network:** GenLayer Studio Network (chain `61999`)

**Live site:** https://pact1.vercel.app

---

## What changed, and why

An earlier version of this project was reviewed and turned down on one point:

> settlement judges mutable, unauthenticated page contents and only records an attestation. For a stronger version, bind evidence to an immutable or signed artifact and connect the verdict to a concrete agreement consequence.

That was correct, and both halves are now closed.

| The criticism | What it is now |
|---|---|
| Evidence was **mutable** — any web page, editable after signing | Evidence must be **one file at one git commit**. The contract rejects branch links outright. The commit hash is a content address, so the bytes cannot be swapped afterwards. |
| Evidence was **unauthenticated** — the drafter picked it unilaterally | The **obligated party** files it, from their own wallet, in a `submit_evidence()` transaction. Who filed it and when are both on-chain. |
| Nothing was **auditable** after the fact | The `sha256` of exactly what the jury read is written to storage. Refetch the pinned URL, hash it, compare. |
| The verdict was **only an attestation** | The verdict **moves the money**. Escrow goes to the counterparty on FULFILLED, back to the funder otherwise. No path leaves it stranded. |

A fifth thing came out of the same work. The old version could be satisfied by a *file name* — a delivered `logo.jpg` passed because a directory listing showed the name, not because anyone looked at the picture. Images are now rendered and actually looked at.

---

## The two things that make a verdict mean something

Most "AI judges your agreement" demos fail on the same two points: the thing being judged can be changed after the fact, and the verdict does not actually do anything. Pact closes both.

### 1. Evidence is pinned, and the obligated party files it themselves

Evidence is **one file at one git commit**:

```
https://raw.githubusercontent.com/<owner>/<repo>/<40-char commit hash>/<path>
```

A commit hash is a hash over the exact tree it names. The bytes served for that hash cannot be swapped later without the hash changing. A branch link like `/main/` points at whatever the branch holds today, which is exactly the hole this closes. The contract **refuses** anything that is not commit-pinned.

The person who **owes** the work files it, from their own wallet, with `submit_evidence()`, before the deadline. That call is a signed on-chain transaction, so who filed it and when are both recorded. They can replace it while the window is open, and it freezes when the window closes. The other party can see exactly what was filed, and has until the deadline to look at it.

For a text artifact, settlement fetches it through `gl.eq_principle.strict_eq`, so **every validator must come back with byte-identical content** before anyone is asked to judge it, and the `sha256` of exactly what was judged is written into contract storage. Anyone can fetch the same pinned URL, hash it, and confirm they are looking at the same bytes the jury read. For an image there is no text to agree on, so the commit hash alone is what fixes the bytes — see below.

### 2. The verdict moves the money

Party A locks an amount of GEN into the pact. The verdict releases it, with no one in the middle:

| Outcome | Where the escrow goes |
|---|---|
| Jury rules **FULFILLED** | to the counterparty |
| Jury rules **NOT FULFILLED** | back to the party who funded it |
| Nothing filed by the deadline | back to the funder, without the model being consulted at all |
| Cancelled before it goes active | back to the funder |

There is no path that ends a pact without moving the escrow. Payment is queued at settlement and lands when the ruling **finalizes**, a few minutes later on the Studio network.

A pact can still be created with an escrow of `0`. The jury still reads and still records a verdict, and the site says plainly that such a pact is a signed record rather than a settlement.

---

## See the jury actually rule

These two pacts are real, live on the chain, and settled by validators that had to agree. Open the site and press either demo button, or open the settle transactions directly. No wallet needed to look.

| Verdict | Pact contract | The jury ruling |
|---|---|---|
| **FULFILLED** | [`0x6736651c…`](https://explorer-studio.genlayer.com/contracts/0x6736651cFba91AAe4f2eeA5aC83f3E646d49e47B) | [settle tx ↗](https://explorer-studio.genlayer.com/tx/0xd1c84d7aaae73562c481276a5b0010b02a4e4c354df04432a9fc85ea48ba91c7) |
| **NOT FULFILLED** | [`0xE8D52E1f…`](https://explorer-studio.genlayer.com/contracts/0xE8D52E1fdc5Ac0A65D96d3164b67231D795e6847) | [settle tx ↗](https://explorer-studio.genlayer.com/tx/0x3f72a4cd50d04bb3b6afa4231f2f422e7f9fb9d310fb9906cba59f941892aa5b) |

**They carry the exact same agreement text.** The only thing that differs is the evidence. Same words, same jury, opposite verdicts. Both are `FINALIZED` with `MAJORITY_AGREE`, and you can see the validator set and their individual votes.

There are also two screen recordings of a full pact lifecycle. Both are **downloads, around 29 MB each** — GitHub serves release files rather than streaming them, so they save to your machine and play locally.

| Recording | What it shows |
|---|---|
| [**fulfilled.mp4** ↓](https://github.com/hossein6191/pact1/releases/download/v1.0/fulfilled.mp4) | Evidence delivered. The jury rules **FULFILLED**. |
| [**notfulfilled.mp4** ↓](https://github.com/hossein6191/pact1/releases/download/v1.0/notfulfilled.mp4) | The *same* agreement text, evidence missing. The jury rules **NOT FULFILLED**. |

> These four were recorded against the previous version, which chose evidence at drafting time and recorded a verdict without moving funds. They still show the jury reading real evidence and ruling honestly, which is the part that did not change. Replacements built on commit-pinned evidence and live escrow are being recorded.

---

## What it does

One person drafts a pact: the agreement in plain language, the counterparty's wallet address, both parties' public identities (X or GitHub), a deadline, and the amount to escrow.

- **Both parties must sign.** The creator signs by deploying. The counterparty opens the same pact address and signs with their own wallet. The pact only becomes **active** once both signatures exist. Each is a real on-chain transaction, not a checkbox.
- **A signature token is minted.** The moment both have signed, the contract mints a deterministic on-chain signature token co-owned by both parties.
- **The counterparty files their proof.** Before the deadline, they name one commit-pinned file as evidence, signed with their own wallet.
- **The AI jury settles it.** After the deadline, either party calls `settle`. Validators read or look at the pinned artifact, judge it against the agreement, and must reach consensus. The verdict, the reason and the content hash are written on-chain, and the escrow is released.

---

## Read this before you write your first pact

### The agreement text *is* the test

The jury reads the **text inside the filed file** and checks it against your words. It is good at facts it can see and cannot judge taste or effort. If your terms do not set a bar, anything that exists will clear it.

| Checkable | Not checkable |
|---|---|
| "the file defines a function named `parse_orders`" | "a *good* implementation" |
| "the article is at least 500 words and mentions X, Y and Z" | "a *professional* tone" |
| "the changelog names feature F under a version above 2.1" | "real effort" |

### Images are judged by looking at them

If the pinned artifact is an image, the jury does not read text. It renders the file, looks at the picture, and answers in a fixed short shape so validators can agree on what they saw.

This closes a real hole. An earlier version of Pact passed a delivered `logo.jpg` purely because a repository listing showed that *file name*. Rendered and actually looked at on Studio, every validator described the same file as an anime portrait of a character with glowing red eyes, and ruled against terms asking for a logo or wordmark.

The rule that keeps this working is the same one that applies to text: **state a visible fact, not a taste.** "The text in the image reads ACME" is checkable. "A good logo" is not, and split validator votes are what you get for asking. The contract tells the model in as many words to judge only what is visibly there.

For an image there is no agreed text to hash, so the digest field holds `git-commit:<hash>` instead. The commit is what fixes the bytes.

### Files the jury can and cannot read

- **Works:** any text-bearing file in a public GitHub repo (source, Markdown, JSON, CSV, plain text), and any image file, which is rendered and looked at instead of read.
- **Fails:** private repos, and anything that is not a commit-pinned `raw.githubusercontent.com` link, because the contract rejects those outright.
- **Quick test:** open the pinned link in a private window. If you can read the content there without signing in, the jury can too.

---

## Why this needs GenLayer

A normal smart contract cannot open a web page or decide whether a real-world agreement was honoured. It only handles facts that reduce to yes or no. Judging "was this delivered as promised" requires reading unstructured evidence and interpreting plain language, which is exactly what a deterministic VM cannot do.

Pact uses four GenLayer capabilities at once: reading the live open web, forcing validators to agree deterministically on what they read, having a model interpret a plain-language agreement against it, and reaching a judgment that multiple validators must agree on before it is recorded — and then acting on that judgment by moving native value.

The trust problem is real and specific: today, two strangers online who disagree about whether a deal was kept have no neutral place to settle it. Escrow platforms solve it by becoming the trusted middleman. Pact removes the middleman instead of replacing it.

---

## How it works (technical)

**`pact.py`** — the Intelligent Contract.

- `_pin_error()` rejects any evidence link that is not a 40-character commit hash on `raw.githubusercontent.com`. Pure, deterministic, and run before anything else.
- `submit_evidence()` is restricted to the obligated party and to the window before the deadline.
- `gl.eq_principle.strict_eq(...)` fetches a text artifact and forces byte-level agreement across validators **before** judgment begins.
- `_is_image()` routes an image artifact down a second path instead: `web.render(url, mode="screenshot")` plus `exec_prompt(..., images=[...])`, under the same custom validator, with the answer held to a fixed short shape so validators can agree on what they saw.
- `genvm-lint check` (the official linter) passes on `pact.py`.
- `hashlib.sha256` of the agreed content is stored in `evidence_digest`, so the ruling is auditable against exact bytes.
- An artifact that comes back empty or missing is ruled `unfulfilled` **before** the model is consulted, so a dead link can never produce a lucky pass.
- `gl.vm.run_nondet_unsafe` with a **custom validator** judges the already-agreed content: the leader asks the model, every validator asks the model itself, and a validator agrees only if its own verdict word is the leader's. The reasoning is free text and is not part of consensus. A crashed leader gets a disagree, so consensus rotates instead of sealing an error.
- `@gl.public.write.payable` + `gl.message.value` take the escrow in; `emit_transfer` pays it out to an ordinary wallet at finalization.
- `_release()` is the single exit for money, and every terminal path calls it.

**`index.html`** — a single-file front end, no backend. The chain is the backend.

- Connects through `genlayer-js` with EIP-6963 wallet discovery.
- **Pins links for you.** Paste any GitHub file link and the site asks GitHub which commit the branch points at, then rewrites it into a pinned raw URL. The same pin rule is also enforced client-side so a mistake costs no transaction.
- **Role-aware.** It reads which party the connected wallet is and only offers what that wallet can legally do — filing evidence is Party B's alone, funding is Party A's.
- Handles the **full transaction lifecycle** rather than trusting a receipt: after every write it polls `get_status` until state actually changes, then tracks the transaction to `FINALIZED`.
- Shows the escrow, who filed the evidence and when, the content hash the jury judged, and where the money went.

### Contract methods

| Method | Who | What it does |
|--------|-----|--------------|
| `fund()` *(payable)* | party A | Locks GEN into the pact. Can be called again to top up. |
| `sign()` | counterparty | Records party B's signature; activates the pact and mints the token once both have signed. |
| `submit_evidence(url)` | counterparty | Files one commit-pinned artifact as proof. Refuses branch links. Replaceable until the deadline. |
| `settle()` | either party | After the deadline: agree on the artifact, record what was judged, rule, and release the escrow. |
| `cancel()` | either party | Cancels before the pact goes active, and refunds the escrow. |
| `get_status()` | view | Full state as JSON, including escrow, evidence, digest and payout destination. |

---

## Run it yourself

1. Open the live site, or host `index.html` on any static host. There is nothing to build.
2. Add the Studio network to your wallet, connect, and press **Get test GEN** — the network funds accounts over its own RPC, so there is no faucet page to queue at.

   ```
   Network name  GenLayer Studio
   RPC URL       https://studio.genlayer.com/api
   Chain ID      61999
   Symbol        GEN
   Explorer      https://explorer-studio.genlayer.com
   ```

3. Draft a pact and fund it, send the address to the other party to sign, let them file their pinned evidence, then settle after the deadline.

Note on testing: consensus transactions take about a minute to reach `ACCEPTED` and a few minutes to `FINALIZED`. The verdict is valid as soon as it is accepted; **the escrow moves at finalization**. Validators can occasionally time out; the front end reports that honestly instead of claiming success, and retrying works.

---

## Path forward

- **Tighter image consensus.** Image judging ships, but a vague visual term still splits validators. Free-form answers fail consensus outright; the fixed short shape the contract asks for is what makes it hold. Guiding people to write visually checkable terms is the remaining work.
- **Multi-file deliveries.** One pinned file covers a lot, but "these three things exist" needs a pinned tree, not a pinned blob.
- **A dispute window.** Party A can currently inspect the filed evidence before the deadline but cannot formally object to it. A short challenge period after filing would make that explicit.
- **Multi-party pacts.** More than two signers, with the jury ruling per obligation instead of per pact.
- **Reusable primitive.** The pin-agree-judge-release pattern here is generic. Extracted cleanly, other builders could drop it into any contract that needs a subjective verdict with a real consequence.

---

Built by **Hellish** · https://x.com/Hellishnum1
