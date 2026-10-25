# Explain it before sending it

The preparation was AI assisted. Reading a prepared note is not evidence that the applicant can independently design or explain the experiment. Run it locally and answer these questions before an interview or an outreach claim about personal mastery.

1. Why does an HMAC prove possession of a key, but not freshness or permission to access another device?
2. Why sign the exact request bytes? What changes if JSON is parsed and reserialized before checking the signature?
3. Why must replay checking and insertion share a critical section? Where is the recording action relative to that section?
4. Why is the nonce keyed by both credential and request ID? What should happen when the same ID arrives with a different body?
5. Why retain a nonce for 61 seconds if freshness permits a 30-second skew? Explain the future-dated boundary case.
6. Why should a rate-rejected request be able to retry after two seconds?
7. Why can an authenticated request still fail scope, URL or tool policy?
8. Why does a URL string passing this parser say nothing about DNS rebinding or the destination of an HTTP redirect?
9. Which observations show actual HTTP execution, and which are only in-memory recorded actions?
10. Why is 60/60 not a security success rate? Which passing rows deliberately show unsafe behavior?
11. What resets on process restart? What would change if two processes shared a durable replay ledger?
12. Which experiments would distinguish duplicate admission from an action committed twice after a crash?

Try changing one expected result or one check and rerunning. Explain the failure using the JSON evidence, then restore the original file. Do not present the current artifact as independent work or as a published-paper reproduction.
