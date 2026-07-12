"""Resume catalog visibility (ADR-0004)."""

from __future__ import annotations

import uuid
from urllib.parse import urlparse

from app.models import Company, Resume, ResumeVisibilityRule
from app.models.enums import ResumeStatus, ResumeVisibility, VisibilityRuleType


def _website_domain(website: str | None) -> str | None:
    if not website:
        return None
    parsed = urlparse(website if "://" in website else f"https://{website}")
    host = parsed.netloc or parsed.path
    return host.removeprefix("www.").lower() or None


def company_matches_hide_rule(company: Company, rule: ResumeVisibilityRule) -> bool:
    if rule.rule_type == VisibilityRuleType.HIDE_COMPANY_ID:
        return str(company.id) == rule.rule_value
    if rule.rule_type == VisibilityRuleType.HIDE_TAX_ID:
        return bool(company.tax_id and company.tax_id == rule.rule_value)
    if rule.rule_type == VisibilityRuleType.HIDE_DOMAIN:
        domain = rule.rule_value.lower()
        website_domain = _website_domain(company.website)
        return website_domain == domain
    return False


def is_resume_blocked(resume: Resume, company_id: uuid.UUID) -> bool:
    return any(block.company_id == company_id for block in resume.blocks)


def is_resume_hidden_from_company(resume: Resume, company: Company) -> bool:
    if is_resume_blocked(resume, company.id):
        return True
    return any(company_matches_hide_rule(company, rule) for rule in resume.visibility_rules)


def is_resume_in_catalog(resume: Resume, company: Company) -> bool:
    if resume.status != ResumeStatus.PUBLISHED:
        return False
    if resume.test_editing:
        return False
    if resume.visibility != ResumeVisibility.PUBLIC:
        return False
    return not is_resume_hidden_from_company(resume, company)


def can_access_link_only_resume(
    resume: Resume, company: Company, *, token: str | None
) -> bool:
    if resume.status != ResumeStatus.PUBLISHED or resume.test_editing:
        return False
    if resume.visibility != ResumeVisibility.LINK_ONLY:
        return False
    if is_resume_hidden_from_company(resume, company):
        return False
    return bool(token and resume.link_token and token == resume.link_token)
