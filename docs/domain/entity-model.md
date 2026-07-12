# Entity Model

Domain entities and database schema for Reverse HH MVP. See [CONTEXT.md](../../CONTEXT.md) for glossary terms.

## ER Diagram

```mermaid
erDiagram
    users ||--o| candidate_profiles : has
    users ||--{ company_members : belongs
    companies ||--{ company_members : has
    companies ||--{ vacancies : has
    companies ||--{ applications : sends
    candidate_profiles ||--{ resumes : owns
    resumes ||--o| tests : has
    resumes ||--{ resume_work_experiences : contains
    resumes ||--{ resume_contacts : has
    resumes ||--{ resume_visibility_rules : has
    resumes ||--{ applications : receives
    tests ||--{ test_questions : has
    test_questions ||--{ test_question_options : has
    vacancies ||--{ vacancy_recruiters : assigns
    vacancies ||--{ applications : used_in
    applications ||--o| chats : opens
    applications ||--{ application_test_answers : has
    chats ||--{ chat_messages : contains
    users ||--{ saved_resumes : saves
    resumes ||--{ saved_resumes : saved_by
    users ||--{ complaints : files
    users ||--{ audit_events : triggers

    users {
        uuid id PK
        string email UK
        string password_hash
        boolean is_admin
        timestamptz created_at
    }

    candidate_profiles {
        uuid id PK
        uuid user_id FK UK
        string display_name
    }

    resumes {
        uuid id PK
        uuid candidate_profile_id FK
        string title
        string status
        string visibility
        jsonb published_data
        jsonb draft_data
        boolean cover_letter_required
        jsonb auto_reject_settings
        timestamptz published_at
        timestamptz archived_at
    }

    companies {
        uuid id PK
        string name
        string website
        string tax_id
        string verification_status
        boolean is_archived
        jsonb profile_data
    }

    vacancies {
        uuid id PK
        uuid company_id FK
        string status
        jsonb data
        uuid created_by FK
    }

    applications {
        uuid id PK
        uuid resume_id FK
        uuid vacancy_id FK
        uuid company_id FK
        uuid sent_by FK
        string status
        jsonb resume_snapshot
        jsonb vacancy_snapshot
        jsonb test_snapshot
        text cover_letter
        timestamptz expires_at
        timestamptz employer_deadline
        timestamptz created_at
    }
```

## Tables

### Auth & users

#### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email | VARCHAR UNIQUE NOT NULL | |
| password_hash | VARCHAR NOT NULL | bcrypt |
| is_admin | BOOLEAN DEFAULT false | platform admin |
| created_at | TIMESTAMPTZ | |

#### `candidate_profiles`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users UNIQUE | one profile per user |
| display_name | VARCHAR | |

### Resumes

#### `resumes`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| candidate_profile_id | UUID FK | |
| title | VARCHAR | e.g. "Backend developer" |
| status | ENUM | `draft`, `published`, `archived`, `deleted` |
| visibility | ENUM | `public`, `link_only`, `hidden` |
| link_token | VARCHAR UNIQUE NULL | for link_only access |
| published_data | JSONB | frozen published fields |
| draft_data | JSONB | working copy |
| cover_letter_required | BOOLEAN | |
| auto_reject_settings | JSONB | salary/format/location modes |
| test_editing | BOOLEAN DEFAULT false | hides from catalog while true |
| published_at | TIMESTAMPTZ NULL | |
| archived_at | TIMESTAMPTZ NULL | |

`published_data` / `draft_data` structure:
- desired_role, industry_id, specialization_id
- skills[], employment_type, work_formats[]
- salary_mode, salary_min, salary_max, salary_currency
- city, country, relocation_countries[]
- about (optional), portfolio_links[], certificate_links[]
- experience_mode: `has_experience` | `no_experience` | `nda`

#### `resume_work_experiences`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| resume_id | UUID FK | references draft or published via resume |
| company_name | VARCHAR NULL | hidden if NDA |
| is_nda | BOOLEAN | |
| role | VARCHAR | |
| started_at | DATE | |
| ended_at | DATE NULL | null = current |
| description | TEXT | max 2000 chars |
| industry_id | UUID NULL | |
| skills | VARCHAR[] | |

Stored inside `draft_data` / `published_data` as array for MVP simplicity, or normalized — implementer may embed in JSONB per ADR-0002 snapshot needs.

#### `resume_contacts`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| resume_id | UUID FK | |
| type | ENUM | phone, email, telegram, linkedin, website, other |
| value | VARCHAR | |
| is_public | BOOLEAN | per-channel visibility |

#### `resume_visibility_rules`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| resume_id | UUID FK | |
| rule_type | ENUM | `hide_company_id`, `hide_domain`, `hide_tax_id` |
| rule_value | VARCHAR | company UUID, domain, or INN |

#### `resume_blocks` (company blocks)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| resume_id | UUID FK | |
| company_id | UUID FK | block all interaction |

### Tests

#### `tests`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| resume_id | UUID FK UNIQUE | one test per resume |
| version | INTEGER | incremented on publish |
| is_published | BOOLEAN | |

#### `test_questions`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| test_id | UUID FK | |
| sort_order | INTEGER | |
| type | ENUM | single_choice, multi_choice, text, scale |
| text | VARCHAR(500) | |
| hint | VARCHAR(1000) NULL | |
| scale_min | INTEGER NULL | |
| scale_max | INTEGER NULL | |
| expected_scale_min | INTEGER NULL | |
| expected_scale_max | INTEGER NULL | |

#### `test_question_options`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| question_id | UUID FK | |
| text | VARCHAR | |
| is_expected | BOOLEAN | for scoring |

Max 10 questions per test (enforced in domain).

### Companies

#### `companies`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | VARCHAR | |
| website | VARCHAR | |
| tax_id | VARCHAR | INN |
| verification_status | ENUM | `pending`, `verified`, `rejected`, `suspended` |
| is_archived | BOOLEAN | |
| profile_data | JSONB | description, industry, size, location |
| application_limit_monthly | INTEGER | subscription limit |
| applications_used_this_month | INTEGER | |

#### `company_members`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| company_id | UUID FK | |
| user_id | UUID FK | |
| role | ENUM | `owner`, `recruiter` |
| UNIQUE(company_id, user_id) | | |

### Vacancies

#### `vacancies`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| company_id | UUID FK | |
| status | ENUM | `draft`, `active`, `archived` |
| created_by | UUID FK → users | |
| data | JSONB | all vacancy fields |

`data` fields: title, salary_fixed, salary_min, salary_max, currency, work_format, city, country, employment_type, responsibilities, requirements, hiring_stages, sender_name, sender_role, benefits (optional), stack (optional).

#### `vacancy_recruiters`
| Column | Type | Notes |
|--------|------|-------|
| vacancy_id | UUID FK | |
| user_id | UUID FK | |
| PRIMARY KEY (vacancy_id, user_id) | | |

### Applications (central)

#### `applications`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| resume_id | UUID FK | |
| vacancy_id | UUID FK | |
| company_id | UUID FK | |
| sent_by | UUID FK → users | recruiter who sent |
| status | ENUM | see state machine doc |
| resume_snapshot | JSONB NOT NULL | |
| vacancy_snapshot | JSONB NOT NULL | |
| test_snapshot | JSONB NULL | |
| cover_letter | TEXT NULL | |
| rejection_reasons | JSONB NULL | candidate reasons if shared |
| expires_at | TIMESTAMPTZ | system 14-day default |
| employer_deadline | TIMESTAMPTZ NULL | employer preferred date |
| extended_once | BOOLEAN DEFAULT false | |
| limit_debited | BOOLEAN | |
| created_at | TIMESTAMPTZ | |
| viewed_at | TIMESTAMPTZ NULL | |
| **UNIQUE(resume_id, vacancy_id)** | | forever |

#### `application_test_answers`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| application_id | UUID FK | |
| question_id | UUID | from snapshot |
| answer_text | TEXT NULL | |
| answer_options | UUID[] NULL | |
| answer_scale | INTEGER NULL | |

### Chat

#### `chats`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| application_id | UUID FK UNIQUE | one chat per application |
| is_read_only | BOOLEAN | block or close_after_acceptance |

#### `chat_messages`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| chat_id | UUID FK | |
| sender_id | UUID FK → users | |
| body | TEXT | text + links only |
| is_hidden | BOOLEAN | moderation |
| created_at | TIMESTAMPTZ | |

### Employer features

#### `saved_resumes`
| Column | Type | Notes |
|--------|------|-------|
| company_id | UUID FK | |
| resume_id | UUID FK | |
| saved_by | UUID FK → users | |
| created_at | TIMESTAMPTZ | |
| PRIMARY KEY (company_id, resume_id) | | |

### Moderation

#### `complaints`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| reporter_id | UUID FK | |
| target_type | ENUM | company, message, application, resume |
| target_id | UUID | |
| body | TEXT | |
| status | ENUM | open, resolved, dismissed |
| created_at | TIMESTAMPTZ | |

#### `moderation_actions`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| complaint_id | UUID FK NULL | |
| admin_id | UUID FK | |
| action_type | VARCHAR | warning, block_user, block_company, etc. |
| target_type | VARCHAR | |
| target_id | UUID | |
| note | TEXT | |
| created_at | TIMESTAMPTZ | |

### Audit & notifications

#### `audit_events`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| actor_id | UUID FK NULL | |
| event_type | VARCHAR | |
| entity_type | VARCHAR | |
| entity_id | UUID | |
| payload | JSONB | |
| created_at | TIMESTAMPTZ | |

#### `notifications`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| type | VARCHAR | |
| body | TEXT | |
| link | VARCHAR NULL | |
| is_read | BOOLEAN DEFAULT false | |
| created_at | TIMESTAMPTZ | |

### Reference data

#### `industries`, `specializations`, `skills`
Standard lookup tables with `id`, `name`, `is_active`. User-proposed values go to `*_pending` queue for admin approval.

## Indexes

- `resumes`: `(status, visibility)` WHERE published; GIN on `published_data` skills; btree on salary fields
- `applications`: `(resume_id, status)`, `(company_id, status)`, `(sent_by)`
- `vacancies`: `(company_id, status)`
- `catalog query`: composite on industry, city, work_format in `published_data`

## Constraints

- `applications`: UNIQUE `(resume_id, vacancy_id)`
- `tests`: max 10 questions — domain validation
- `vacancies`: salary_fixed OR (salary_min AND salary_max) required when active
- `resumes`: experience validation per experience_mode
