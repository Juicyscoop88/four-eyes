---
name: ship
description: Ship a change through the Four Eyes software factory - the person's request becomes an issue, the autopilot does the rest (plan, blind tests, code, gate) and comes back with decision cards. Use when the person asks to ship, implement or build something in this repo.
argument-hint: "<what should change and why>"
---

The person's request: $ARGUMENTS

You do not implement this yourself. The factory does, and nobody checks their own work: an author agent
writes the code, a tester writes the tests without ever seeing it, a reviewer reads the diff
without seeing the conversation, and the gate measures it all.

1. **Issue.** Write the request as `issues/<short-name>.md`: a title line and two to four sentences in the
   person's words, what should change and why. Show it to the person and wait for their go; this is where
   they steer. Then commit it.
2. **Autopilot.** Run `foureyes autopilot issues/<short-name>.md`. It works on the branch
   `factory/<short-name>` and takes a few minutes.
3. **Report.** Read `.factory/runs/<short-name>.md`. Tell the person in a few lines whether the gate passed
   and what the tests caught, then show each decision card with its answers.
4. **Decisions.** For each card the person answers, run
   `foureyes decide <short-name> <card> <answer>`. Their answer becomes a blind test first, then code.
5. **Wheel.** If the person wants to change something by hand, they can: the branch is theirs. Running step 2
   again continues from where they left it.

Opening the pull request and approving it are the person's: an agent never approves.
