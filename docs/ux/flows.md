# UX Flows

Text wireframes for MVP screens. Language: Russian UI. See [PRD](../prd/reverse-hh-prd.md).

---

## 1. Registration / Login

**Pages:** `/pages/login.html`, `/pages/register.html`

### Register
- Fields: email, password, confirm password, display name
- Button: «Зарегистрироваться»
- Link: «Уже есть аккаунт? Войти»
- On success → redirect to role hub (`/index.html`)

### Login
- Fields: email, password
- Button: «Войти»
- On success → `GET /auth/me` → redirect to role hub

### Role hub (`/index.html`)
- If has candidate profile: link «Я соискатель»
- If member of companies: list workspaces «Я работодатель → {company}»
- Link: «Создать профиль соискателя» / «Создать компанию»

---

## 2. Resume create & publish

**Page:** `/pages/candidate/resume-edit.html`

### Sections
1. **Основное:** желаемая роль, отрасль (select), специализация (select + предложить), навыки (tags)
2. **Условия:** форматы работы (checkboxes), город/страна, релокация, занятость
3. **Зарплата:** режим (вилка / минимум / обсуждается / скрыто для каталога), суммы, валюта
4. **Опыт:** режим (есть / нет / NDA) → список мест работы (добавить/удалить)
5. **Контакты:** каналы + чекбокс «показывать публично» на каждый
6. **Видимость:** всем / по ссылке / никому; скрыть от компании/домена/ИНН
7. **Автоотказ:** по зарплате, формату, городу — режим «помечать» или «автоотказ»
8. **Сопроводительное письмо:** обязательно / необязательно для работодателя
9. **О себе** (optional), портфолио, сертификаты (optional links)

### Actions
- «Сохранить черновик» → PATCH draft, stay on page
- «Опубликовать» → validate → publish → list resumes
- Warning if contacts in free text fields detected (non-blocking)

**List:** `/pages/candidate/resumes.html` — cards with status, edit, archive, delete

---

## 3. Test constructor

**Page:** `/pages/candidate/test-edit.html?resume_id=`

### On enter
- Resume auto-hidden (`test_editing=true`) — banner: «Резюме скрыто из каталога на время редактирования теста»

### UI
- List questions (max 10), drag order
- Add question: тип (один / несколько / текст / шкала 1-5 или 1-10)
- Per question: текст, подсказка, варианты + «ожидаемый» для closed; диапазон для шкалы
- All questions required (no per-question toggle)

### Actions
- «Сохранить черновик» — resume stays hidden
- «Сохранить и вернуть в каталог» — validate, publish test, restore visibility
- «Удалить тест» — modal confirm → delete, future applications without test

---

## 4. Employer catalog

**Page:** `/pages/employer/catalog.html`

**Prerequisite:** company verified, active workspace selected (`X-Company-Id`)

### Filters (sidebar)
- Отрасль, специализация, навыки, город/страна, формат, релокация, занятость, зарплата (range), дата обновления, поиск по тексту

### Resume card
- Role, skills, experience summary, salary (per visibility), formats, city
- NO indicator if test exists
- Buttons: «Откликнуться», «Сохранить»

### Direct link
- `/pages/employer/resume.html?id=` or `?token=` for link_only resumes

---

## 5. Employer application (отклик)

**Page:** `/pages/employer/apply.html?resume_id=`

### Steps
1. **Select vacancy** — dropdown active vacancies only; show validation errors if incomplete
2. **Pre-checks** — API returns: can_apply, warnings (salary mismatch, auto-reject risk, external contacts in vacancy)
3. **Test** (if resume has test) — questions rendered from API; employer does NOT see scoring
4. **Cover letter** — textarea 300-3000 chars if required; optional otherwise
5. **Submit** — confirm dialog if warnings

### After submit
- Success → application detail or list
- No draft: leaving page loses progress

### Blocked cases (UI message)
- Already applied this vacancy
- Company blocked
- Resume hidden
- No application limit
- Company not verified

---

## 6. Candidate inbox

**Page:** `/pages/candidate/applications.html`

### Filters
- По резюме, компании, статусу, дате, зарплате вакансии, формату

### Application card
- Company name, verification badge, vacancy title, salary, format
- Test match summary (for candidate only)
- Cover letter
- Risk badge if external contacts detected
- Mismatch badges (salary/format/location)
- Status label

### Actions (by status)
- `sent`/`viewed`/`reactivated`: «Принять» (confirm), «Отклонить» (confirm + optional reasons multi-select + share checkbox)
- `expired`: «Интересно, актуально?»
- `accepted`: link to chat, «Отказаться от общения»
- Archive/hide old items

**Detail:** `/pages/candidate/application.html?id=`

---

## 7. Chat

**Page:** `/pages/chat.html?application_id=`

### Layout
- Header: company/candidate name, vacancy, status
- Message list: sender name, timestamp, body (links clickable, external warning)
- Input: textarea + «Отправить» (disabled if read-only)

### Read-only when
- `closed_after_acceptance`
- company blocked
- admin action

### Contacts
- Button «Поделиться контактами» (candidate) — sends selected public contacts as message
- No auto-reveal

---

## 8. Company workspace

**Pages:**
- `/pages/employer/company.html` — profile, verification status
- `/pages/employer/vacancies.html` — list CRUD
- `/pages/employer/vacancy-edit.html` — all required fields
- `/pages/employer/members.html` — invite, approve join requests
- `/pages/employer/applications.html` — outbound applications

### Verification form
- Company name, website, tax_id (readonly if set), email domain check status
- Banner if pending manual review (2nd+ company)

### Vacancy status
- draft / active / archive — only owner + creator change status
- assigned recruiters can edit content

### Company profile (shown to candidate on application)
- Name, site, description, industry, size, location, verified badge, sender info
- Serious violations warning if flagged

---

## Global UI patterns

- Minimal CSS: single `main.css`, system fonts, high contrast
- Confirm modals on destructive/final actions (accept, reject, delete, block)
- Toast or banner for API errors
- 401 → redirect login
- Empty states with short explanation
