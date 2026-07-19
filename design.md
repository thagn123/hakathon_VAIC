# UI contract — Corporate Credit Request

## Users and jobs

- Customer User: submit structured credit information and track status.
- Credit Appraisal Agent (#1): transparent credit recommendation at submit; never approve.
- RM: review appraisal, optionally note, forward to Credit Specialist.
- Service Advisory Agent (#2): recommend accompanying services at RM forward; never approve.
- Credit Specialist: review both recommendations and explicitly approve, reject, or return to RM.

## Screen placement

- Customer portal: one corporate credit form (create + reopen submitted requests).
- RM / Credit Specialist: same form layout (readonly fields + Agent #1/#2 + role actions).
- No separate approval-only cards — agent and human act on the same tờ trình form.

## States

`WithRM` (agent #1 done) → RM forward → `PendingApproval` (agent #2 done) → final `Approved` / `Rejected`.
`needs_more_information` returns the request to `WithRM`.

## Safety

- Role and customer scope are checked by the API, not the UI.
- Every write requires an idempotency key.
- Agent output is labeled as a recommendation.
- Final decision requires Credit Specialist identity and a written reason.
