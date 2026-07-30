# Pact — Agreements the Internet Can Judge

**Two people write a deal in plain words, both sign it with their own wallets, and after the deadline a jury of AI validators reads the evidence online and rules whether the agreement was kept.**

**Network:** GenLayer Bradbury Testnet

**Live site:** _add your deployment URL here_
**Demo video:** _add your video link here_

### See it work without deploying anything

Open the site and press **"View a real completed pact"**. No wallet needed. It loads this real pact live from the chain:

```
0x24052Dd08728ceED8DC3640D52e01Cc683b93596
```

That pact already ran the entire lifecycle on Bradbury: both parties signed with their own wallets, the signature token was minted, and after the deadline the AI jury read the evidence page and returned a verdict that is now finalized on-chain. Every field shown is read live via `get_status`, and the settle transaction is verifiable on the Bradbury explorer.

---

## What it does

One person drafts a pact: the agreement in plain language, the counterparty's wallet address, both parties' public identities (X or GitHub), an evidence URL, and a deadline.

- **Both parties must sign.** The creator signs by deploying. The counterparty opens the same pact address and signs with their own wallet. The pact only becomes **active** once both signatures exist. Each one is a real on-chain transaction, not a checkbox.
- **A signature token is minted.** The moment both have signed, the contract mints a deterministic on-chain signature token co-owned by both parties — a permanent record that these two identities signed this exact agreement.
- **The AI jury settles it.** After the deadline, either party can call `settle`. Validators independently read the live evidence page, judge whether the agreement was met, and must reach consensus. The verdict and a reason are written on-chain.

This maps to two of GenLayer's own suggested use cases: private peer-to-peer contracts, and AI arbitration.

---

## Why this needs GenLayer

A normal smart contract cannot open a web page or decide whether a real-world agreement was honoured. It only handles facts that reduce to yes or no. Judging "was this delivered as promised" requires reading unstructured evidence and interpreting plain language, which is exactly what a deterministic VM cannot do.

Pact uses three GenLayer capabilities at once: reading the live open web, understanding a plain-language agreement, and reaching a judgment that multiple validators must agree on before it is recorded.

The trust problem is real and specific: today, two strangers online who disagree about whether a deal was kept have no neutral place to settle it. Escrow platforms solve it by becoming the trusted middleman. Pact removes the middleman instead of replacing it.

---

## How it works (technical)

**`pact.py`** — the Intelligent Contract.

- `gl.nondet.web.render(url, mode="text")` reads the live evidence page.
- `gl.nondet.exec_prompt(...)` asks the model whether the agreement was met, constrained to a single lowercase word.
- `gl.eq_principle.strict_eq(...)` runs that across validators and requires agreement before the verdict is accepted.
- The minted token id and the stored reason are both derived deterministically, so validators cannot disagree on them.

**`index.html`** — a single-file front end, no backend. The chain is the backend.

- Connects through `genlayer-js` with EIP-6963 wallet discovery, so multiple installed wallets can coexist.
- Handles the **full transaction lifecycle** rather than trusting a receipt: after every write it polls `get_status` until the contract state actually changes, then tracks the transaction to `FINALIZED` and upgrades the UI from *finalizing* to *confirmed*.
- **Role-aware.** It reads which party the connected wallet is and only offers actions that wallet can legally take, which prevents double-signing and failed transactions.
- Shows the jury's reason for a verdict, and explains that a *not fulfilled* result can also mean the evidence URL pointed at the wrong page.

### Contract methods

| Method | Who | What it does |
|--------|-----|--------------|
| `sign()` | counterparty | Records party B's signature; activates the pact and mints the signature token once both have signed. |
| `settle()` | either party | After the deadline, asks the AI jury to read the evidence and rule fulfilled / not fulfilled. |
| `cancel()` | either party | Cancels the pact, only allowed before it becomes active. |
| `get_status()` | view | Returns the full current state as JSON, including the minted token. |

> **Scope note:** this version records a verdict and does not move funds. Contract-to-wallet native transfers are not currently workable on Bradbury, so Pact was deliberately built as judgment-only rather than shipping an escrow path that cannot settle.

---

## Run it yourself

1. Open the live site, or host `index.html` on any static host. There is nothing to build.
2. Connect a wallet on GenLayer Bradbury and get test GEN from the faucet.
3. Draft a pact, send the address to the other party to sign, then settle after the deadline.

Note on testing: Bradbury consensus transactions can take minutes and occasionally time out at the network level. The front end reports this honestly instead of claiming success, and retrying works. Full finalization usually takes around 30 minutes, and the verdict is valid before that.

---

## Path forward

- **Escrow and payout.** The judgment layer works today. Once native contract-to-wallet transfers are usable, the same verdict can release or refund funds automatically, which turns Pact from a verdict into a settlement.
- **Agreement templates.** A library of common deal types (delivery, milestone, referral, bet) so users pick a pattern instead of writing terms from scratch.
- **Multi-party pacts.** More than two signers, with the jury ruling per obligation instead of per pact.
- **Reusable primitive.** The judge-and-consensus pattern here is generic. Extracted cleanly, other builders could drop it into any contract that needs a subjective verdict.

Pact was built before the ecosystem's adjudication push became public, and it points the same direction: agreements that a decentralized network can interpret and rule on. This one is aimed at people rather than agents, which makes it a consumer-facing surface for the same primitive.

---

Built by **Hellish** · https://x.com/Hellishnum1
