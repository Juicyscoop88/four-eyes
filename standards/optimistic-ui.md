# Optimistic UI

People should never wait for the server to see what they just did.

- An action shows its result at once and marks it pending until the server confirms.
- If the server refuses, the change rolls back visibly and says why, in one sentence.
- Never optimistic for money movements or orders: those show "sending" until confirmed.
