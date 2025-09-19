.PHONY: dryrun match review
dryrun:
	@bin/flow policy_auto
match:
	@bin/flow policy_match
review:
	@bin/flow policy_review
