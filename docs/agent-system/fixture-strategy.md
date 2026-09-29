# Fixture Strategy

Fixtures are part of product quality, not test decoration.

## Required fixture families

### Architectural planning
- common 30x50 / 50x30 residential plot
- compact site
- irregular/adverse dimensions supported by current contracts
- parking-heavy program
- bedroom-heavy program
- circulation repair case
- site-space accounting case
- soft wet-stack conflict
- AI preferred-size conflict with deterministic feasibility

### Existing-plan intake
- valid JPG
- valid PNG
- valid PDF
- unsupported file
- corrupt file
- incomplete/missing orientation
- ambiguous dimensions
- provider malformed output
- provider timeout/error

### Auth/persistence
- owner reads own project
- foreign user denied
- stale revision conflict
- restart/reload
- missing JWT
- wrong audience
- expired/invalid token

### Billing/payment
- free first generation
- second free project denied
- successful PhonePe payment
- pending payment
- failed payment
- duplicate webhook
- replay attempt
- forged webhook
- missing signature
- production with PhonePe and no Razorpay
- development billing bypass
- production dev-bypass rejection

## Fixture quality rules
- deterministic IDs/times when useful
- no production secrets
- realistic domain values
- smallest case that proves behavior
- explain why a regression fixture exists
