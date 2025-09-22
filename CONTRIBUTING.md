# Contributing to mcp-map-company

Thank you for your interest in contributing to mcp-map-company! This document provides guidelines for contributing to this documentation and automation-focused project.

## 🚫 NO-DEPLOY Policy

**IMPORTANT**: This project follows a strict **NO-DEPLOY** policy. All contributions must be limited to:
- Documentation improvements
- Automation and tooling enhancements
- CI/CD pipeline improvements
- Testing and quality assurance

## 🌿 Branch Strategy

### Main Branch
- **main**: Production-ready documentation and automation
- Always use merge commits (not squash or rebase)
- Requires pull request review before merging

### Feature Branches
- Use descriptive names: `feature/description` or `docs/topic`
- Examples:
  - `feature/ci-automation`
  - `docs/security-guidelines`
  - `fix/link-validation`

### Naming Conventions
- **feature/**: New functionality or automation
- **docs/**: Documentation updates
- **fix/**: Bug fixes or corrections
- **chore/**: Maintenance tasks

## 🏷️ Issue Labels

### Priority Labels
- `priority/critical`: Critical issues requiring immediate attention
- `priority/high`: High priority items for next sprint
- `priority/medium`: Medium priority items
- `priority/low`: Low priority or nice-to-have items

### Type Labels
- `type/documentation`: Documentation improvements
- `type/automation`: CI/CD and automation work
- `type/bug`: Bug reports and fixes
- `type/enhancement`: Feature requests and improvements

### Policy Labels
- `no-deploy`: **REQUIRED** - Confirms no production deployment
- `docs-only`: Documentation-only changes
- `automation-only`: Automation/tooling changes only

### Status Labels
- `status/in-progress`: Currently being worked on
- `status/blocked`: Blocked by dependencies
- `status/review-needed`: Ready for review
- `status/needs-info`: Requires additional information

## 📝 Pull Request Process

### Before Creating a PR

1. **Run Local Checks** (Required):
   ```bash
   # Link validation
   make incident-links

   # Integrity audit
   make incident-audit
   ```

2. **Document Changes**: Update relevant documentation
3. **Add Labels**: Include `no-deploy` label
4. **Link Audit**: If changing documentation, run link audit

### PR Title Format
Use conventional commit format:
```
<type>(<scope>): <description>

Examples:
docs(security): add security policy guidelines
feat(ci): implement automated testing pipeline
fix(links): resolve broken documentation links
```

### PR Description Template
```markdown
## Summary
Brief description of changes

## Type of Change
- [ ] Documentation update
- [ ] Automation/CI improvement
- [ ] Bug fix
- [ ] Process improvement

## Checklist
- [ ] I have run `make incident-links` locally
- [ ] I have run `make incident-audit` locally
- [ ] I have added the `no-deploy` label
- [ ] I have updated relevant documentation
- [ ] My changes follow the coding standards
- [ ] I have tested my changes locally

## Policy Confirmation
- [ ] ✅ **NO-DEPLOY**: This PR contains no production deployment changes
```

### Review Requirements
- **Required Reviews**: 1 reviewer minimum
- **Required Checks**: All CI checks must pass
- **Link Validation**: `make incident-links` must pass
- **Integrity Check**: `make incident-audit` must pass

## 📁 File Organization

### Documentation Structure
```
REPORTS/incident-center/
├── INDEX.md                 # Main index
├── v1.0.1-pre/             # Version-specific reports
├── v1.0.2-planning/        # Planning documents
└── WEEKLY/                 # Weekly monitoring reports
```

### Required Path Naming
- **REPORTS**: Always use uppercase `REPORTS/` (not `reports/`)
- **Validation**: Pre-commit hooks enforce correct casing
- **Script**: `scripts/check_reports_casing.sh` validates paths

## 🔗 Link Management

### Link Audit Requirements
- **Mandatory**: Run `make incident-links` before PR submission
- **Validation**: All internal links must be valid
- **External Links**: GitHub links should return HTTP 200
- **Documentation**: Update `LINK_AUDIT.md` for significant changes

### Link Guidelines
- Use relative paths for internal documentation
- Prefer Markdown reference-style links for readability
- Include descriptive link text (not "click here")
- Validate external links before adding

## 🧪 Testing Guidelines

### Local Testing
```bash
# Run all checks
make incident-links    # Link validation
make incident-audit   # Integrity checking

# Individual checks
make link-audit       # Basic link audit
make link-audit-strict # Strict mode (no 404s allowed)
```

### Documentation Testing
- Spell check using `aspell` or similar
- Markdown linting with `markdownlint`
- Link validation with custom scripts

## 📊 Quality Standards

### Documentation Quality
- **Clarity**: Write for your audience
- **Accuracy**: Verify all technical information
- **Completeness**: Include all necessary details
- **Consistency**: Follow established patterns

### Code Quality (Automation)
- **Shell Scripts**: Use shellcheck for validation
- **YAML**: Validate GitHub Actions workflows
- **Markdown**: Follow CommonMark specification

## 🔄 Workflow Integration

### GitHub Actions
- All PRs trigger automated checks
- Link validation runs on every change
- Integrity checks ensure document consistency
- Weekly monitoring validates ongoing system health

### Local Development
```bash
# Setup (one-time)
git clone https://github.com/youareplan-ceo/mcp-map-company.git
cd mcp-map-company

# Before each PR
make incident-links
make incident-audit

# Create feature branch
git checkout -b feature/your-feature
```

## 🆘 Getting Help

### Documentation Questions
- Create issue with `type/documentation` label
- Reference specific files or sections
- Include context about your use case

### Technical Issues
- Create issue with `type/bug` label
- Include steps to reproduce
- Provide system information if relevant

### Process Questions
- Create issue with `support` label
- Ask in discussions for general questions
- Contact maintainers for urgent issues

## 📞 Contact

- **Issues**: Use GitHub Issues for all requests
- **Discussions**: Use GitHub Discussions for general questions
- **Email**: For sensitive matters only

---

**Last Updated**: 2025-09-22 15:30:00 KST (Asia/Seoul)
**Policy**: 🚫 NO-DEPLOY - Documentation and automation only
**Review**: This document is reviewed quarterly