"""Domain enum types matching docs/domain/entity-model.md."""

from enum import StrEnum


class ResumeStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ResumeVisibility(StrEnum):
    PUBLIC = "public"
    LINK_ONLY = "link_only"
    HIDDEN = "hidden"


class ExperienceMode(StrEnum):
    HAS_EXPERIENCE = "has_experience"
    NO_EXPERIENCE = "no_experience"
    NDA = "nda"


class ContactType(StrEnum):
    PHONE = "phone"
    EMAIL = "email"
    TELEGRAM = "telegram"
    LINKEDIN = "linkedin"
    WEBSITE = "website"
    OTHER = "other"


class VisibilityRuleType(StrEnum):
    HIDE_COMPANY_ID = "hide_company_id"
    HIDE_DOMAIN = "hide_domain"
    HIDE_TAX_ID = "hide_tax_id"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class CompanyMemberRole(StrEnum):
    OWNER = "owner"
    RECRUITER = "recruiter"


class InviteStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"


class JoinRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class VacancyStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ApplicationStatus(StrEnum):
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AUTO_REJECTED = "auto_rejected"
    EXPIRED = "expired"
    REACTIVATION_REQUESTED = "reactivation_requested"
    REACTIVATED = "reactivated"
    CLOSED_AFTER_ACCEPTANCE = "closed_after_acceptance"


class QuestionType(StrEnum):
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    TEXT = "text"
    SCALE = "scale"


class ComplaintTargetType(StrEnum):
    COMPANY = "company"
    MESSAGE = "message"
    APPLICATION = "application"
    RESUME = "resume"


class ComplaintStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
