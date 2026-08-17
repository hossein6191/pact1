# Pact — Agreements the Internet Can Judge

**Two people write a deal in plain words, both sign it with their own wallets, and after the deadline a jury of AI validators reads the evidence online and rules whether the agreement was kept.**

**Network:** GenLayer Studio Network (chain `61999`)

**Live site:** https://pact1.vercel.app

### Watch it run

Two screen recordings of a real pact going through its whole life on the Studio network. Both are **downloads, around 29 MB each** — GitHub serves release files rather than streaming them, so they save to your machine and play locally.

| Recording | What it shows |
|---|---|
| [**fulfilled.mp4** ↓](https://github.com/hossein6191/pact1/releases/download/v1.0/fulfilled.mp4) | The evidence page contains the delivered file. The jury rules **FULFILLED**. |
| [**notfulfilled.mp4** ↓](https://github.com/hossein6191/pact1/releases/download/v1.0/notfulfilled.mp4) | The *same* agreement text, pointed at a repository without the file. The jury rules **NOT FULFILLED**. |

Watched together they make the point the project rests on: identical words, identical jury, opposite verdicts, decided by what was actually on the page.

In a hurry? The two demo buttons below do the same thing in one click, live from the chain, with nothing to download.

### See it work without deploying anything

Open the site and press either demo button. No wallet needed. They load two real pacts live from the chain — and each one links straight to its verdict on the explorer, so you never have to take this page's word for anything.

| Verdict | Pact contract | The jury ruling |
|---|---|---|
| **FULFILLED** | [`0x6736651c…`](https://explorer-studio.genlayer.com/contracts/0x6736651cFba91AAe4f2eeA5aC83f3E646d49e47B) | [settle tx ↗](https://explorer-studio.genlayer.com/tx/0xd1c84d7aaae73562c481276a5b0010b02a4e4c354df04432a9fc85ea48ba91c7) |
| **NOT FULFILLED** | [`0xE8D52E1f…`](https://explorer-studio.genlayer.com/contracts/0xE8D52E1fdc5Ac0A65D96d3164b67231D795e6847) | [settle tx ↗](https://explorer-studio.genlayer.com/tx/0x3f72a4cd50d04bb3b6afa4231f2f422e7f9fb9d310fb9906cba59f941892aa5b) |

These two are the whole argument for the project. **They carry the exact same agreement text.** The only thing that differs is the evidence URL — one repository had the delivered file, the other did not. Same words, same jury, opposite verdicts. That is the difference between a model rubber-stamping whatever it is handed and a jury that actually reads.

Open both settle transactions side by side. Each is `FINALIZED` with `MAJORITY_AGREE`, and you can see the validator set, their individual votes, and the recorded result. Both pacts ran the entire lifecycle: two wallets signed, the signature token was minted, and after the deadline the jury read the evidence page and returned a verdict now final on-chain. Every field the site shows is read live via `get_status`.

---

## What it does

One person drafts a pact: the agreement in plain language, the counterparty's wallet address, both parties' public identities (X or GitHub), an evidence URL, and a deadline.

- **Both parties must sign.** The creator signs by deploying. The counterparty opens the same pact address and signs with their own wallet. The pact only becomes **active** once both signatures exist. Each one is a real on-chain transaction, not a checkbox.
- **A signature token is minted.** The moment both have signed, the contract mints a deterministic on-chain signature token co-owned by both parties — a permanent record that these two identities signed this exact agreement.
- **The AI jury settles it.** After the deadline, either party can call `settle`. Validators independently read the live evidence page, judge whether the agreement was met, and must reach consensus. The verdict and a reason are written on-chain.

This maps to two of GenLayer's own suggested use cases: private peer-to-peer contracts, and AI arbitration.

---

## Read this before you write your first pact

Two things decide whether a pact means anything. Neither is obvious, and both are now explained inside the app itself.

### The agreement text *is* the test

The jury reads the **text** of your evidence page and checks it against your words. It is good at facts it can see and cannot judge taste or effort. If your terms do not set a bar, anything that exists will clear it — a one-line article is still an article.

| Checkable | Not checkable |
|---|---|
| "a file named `logo.svg` exists in the repo" | "a *good* logo" |
| "the post is at least 500 words and mentions X, Y and Z" | "a *professional* website" |
| "the issues page shows #12 and #14 as Closed" | "real effort" |

**Images cannot be judged at all.** `mode="text"` returns nothing for an image URL — measured, not assumed. The jury can confirm an image file is *there*; it can never see what the picture looks like. Agree the picture between yourselves and use the pact for the part a machine can verify.

### Whoever controls the evidence page controls the verdict

Party A drafts the pact *and* picks the evidence URL. If A also owns that page, A can put anything on it and the pact proves nothing.

A pact is only meaningful when the evidence URL points somewhere **the counterparty controls**, or somewhere neutral, and is fixed **before** the work happens. The protection is that party B sees the terms, the evidence URL and the deadline in the signing document and must tick *"I have read this agreement"* before `sign()` goes through. **B consents to the evidence URL.** Sign blindly and that protection is gone.

### Pages the jury can and cannot read

- **Works:** GitHub files and repos, `raw.githubusercontent.com`, blog posts, docs, any plain public web page.
- **Fails:** X/Twitter, Instagram, LinkedIn, Discord, private Google Docs. These block automated reading, so the jury sees an empty page.
- **Quick test:** open the link in a private window. If you can see the proof without signing in, the jury can too.

---

## Why this needs GenLayer

A normal smart contract cannot open a web page or decide whether a real-world agreement was honoured. It only handles facts that reduce to yes or no. Judging "was this delivered as promised" requires reading unstructured evidence and interpreting plain language, which is exactly what a deterministic VM cannot do.

Pact uses three GenLayer capabilities at once: reading the live open web, understanding a plain-language agreement, and reaching a judgment that multiple validators must agree on before it is recorded.

The trust problem is real and specific: today, two strangers online who disagree about whether a deal was kept have no neutral place to settle it. Escrow platforms solve it by becoming the trusted middleman. Pact removes the middleman instead of replacing it.

---

## How it works (technical)

**`pact.py`** — the Intelligent Contract.

- `gl.nondet.web.render(url, mode="text")` reads the live evidence page.
- A page that renders to almost nothing — an image URL, a login wall, a dead link — is ruled `unfulfilled` **before** the model is consulted, so an empty page can never produce a lucky pass.
- `gl.nondet.exec_prompt(...)` asks the model whether the agreement was met, constrained to a single lowercase word.
- `gl.eq_principle.strict_eq(...)` runs that across validators and requires agreement before the verdict is accepted.
- The minted token id and the stored reason are both derived deterministically, so validators cannot disagree on them.

**`index.html`** — a single-file front end, no backend. The chain is the backend.

- Connects through `genlayer-js` with EIP-6963 wallet discovery, so multiple installed wallets can coexist.
- Handles the **full transaction lifecycle** rather than trusting a receipt: after every write it polls `get_status` until the contract state actually changes, then tracks the transaction to `FINALIZED` and upgrades the UI from *finalizing* to *confirmed*.
- **Role-aware.** It reads which party the connected wallet is and only offers actions that wallet can legally take, which prevents double-signing and failed transactions.
- Every pact is its own contract, deployed from the browser by whoever drafts it, so no two agreements share state.
- Shows the jury's reason for a verdict, and explains that a *not fulfilled* result can also mean the evidence URL pointed at the wrong page.

### Contract methods

| Method | Who | What it does |
|--------|-----|--------------|
| `sign()` | counterparty | Records party B's signature; activates the pact and mints the signature token once both have signed. |
| `settle()` | either party | After the deadline, asks the AI jury to read the evidence and rule fulfilled / not fulfilled. |
| `cancel()` | either party | Cancels the pact, only allowed before it becomes active. |
| `get_status()` | view | Returns the full current state as JSON, including the minted token. |

> **Scope note:** this version records a verdict and does not move funds. That was forced by the previous network, where contract-to-wallet native transfers did not work. On the Studio network the shipped `faucet.py` example performs exactly that transfer on the same contract stdlib Pact uses, so escrow is now a genuine next step rather than a closed door — it needs its own testing before being claimed.

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

3. Draft a pact, send the address to the other party to sign, then settle after the deadline.

Note on testing: consensus transactions take about a minute to reach `ACCEPTED` and a few minutes to `FINALIZED`. The verdict is valid as soon as it is accepted. Validators can occasionally time out; the front end reports that honestly instead of claiming success, and retrying works.

---

## Path forward

- **Escrow and payout.** The judgment layer works today. The same verdict can release or refund funds automatically, which turns Pact from a verdict into a settlement — see the scope note above.
- **Judging images.** `mode="screenshot"` plus `exec_prompt(..., images=[...])` would let the jury see a delivered design instead of only confirming the file exists. This is the single biggest gap between what Pact judges and what people actually agree about.
- **Agreement templates.** The built-in suggestions now all state a measurable bar rather than a vague brief. Growing that into a proper library means users pick a pattern instead of learning the hard way that "a good logo" always passes.
- **Multi-party pacts.** More than two signers, with the jury ruling per obligation instead of per pact.
- **Reusable primitive.** The judge-and-consensus pattern here is generic. Extracted cleanly, other builders could drop it into any contract that needs a subjective verdict.

Pact was built before the ecosystem's adjudication push became public, and it points the same direction: agreements that a decentralized network can interpret and rule on. This one is aimed at people rather than agents, which makes it a consumer-facing surface for the same primitive.

---

Built by **Hellish** · https://x.com/Hellishnum1
