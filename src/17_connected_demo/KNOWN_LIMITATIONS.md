# Known Limitations — Project Witness Connected Demo v0.1

- one case per run
- drives the frozen CLIs by subprocess (the real integration path)
- the default selfcheck and unit tests use a fixture runner and spawn no subprocess
- does not modify any frozen component
- does not copy evidence contents
- does not prove truth
- does not prove the stack works in the real world; it records reported statuses only
- reaches DEMO_COMPLETED only when every required terminal status is observed
