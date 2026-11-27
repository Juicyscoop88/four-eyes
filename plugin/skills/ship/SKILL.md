---
name: ship
description: Hand a change over to the Four Eyes software factory - the person's request becomes an issue, the autopilot does the rest (plan, blind tests, code, gate) and comes back with decision cards. Use when the person wants the factory to build it, hands a change over, or says ship. When they ask you to write or fix code yourself, do it as usual (the factory's rules still reach you per file); for a larger change offer once to hand it to the factory instead, so that someone who never saw the code writes the tests.
argument-hint: "<what should change and why>"
---

The person's request: $ARGUMENTS

You do not implement this yourself. The factory does, and nobody checks their own work: an author agent
writes the code, a tester writes the tests without ever seeing it, a reviewer reads the diff
without seeing the conversation, and the gate measures it all.

1. **Issue, shaped with the person.** The tester will write tests from this issue alone, never seeing the
   code, so it must say what "done" looks like. Help the person get there in one short round, in their
   language and their words, never as a form:
   - Write `issues/<short-name>.md`: a title line, then **What** (what should change, two or three
     sentences), **Why** (who needs it and what goes wrong today: the result is checked against this) and
     **Example** (one concrete case with numbers and the expected outcome, like "an order for 10, 4 filled,
     changed to 12: it still needs 8"). If the person gave no example, propose one from what they said and
     mark it as your proposal.
   - Below it, list at most three **open questions** where the issue is silent and a test would have to
     guess (an edge case, a limit, what happens on bad input), each with the answer you would assume.
   - Show both and ask the person to confirm, correct the example, or answer any question. A question they
     skip stays an assumption: the plan writes it as a card (A1, A2..) they can still change on the pull
     request. Never ask more than one round; a short issue is fine.
   Then commit it.
2. **Autopilot.** Run `foureyes autopilot issues/<short-name>.md`. It works on the branch
   `factory/<short-name>` and takes a few minutes.
3. **Report.** Read `.factory/runs/<short-name>.md`. Tell the person in a few lines whether the gate passed
   and what the tests caught, then show each decision card with its answers.
4. **Decisions.** For each card the person answers, run
   `foureyes decide <short-name> <card> <answer>`. Their answer becomes a blind test first, then code.
5. **Wheel.** If the person wants to change something by hand, they can: the branch is theirs. Running step 2
   again continues from where they left it.

Opening the pull request and approving it are the person's: an agent never approves.
