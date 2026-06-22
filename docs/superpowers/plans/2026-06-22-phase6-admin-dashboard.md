# Phase 6: Admin Dashboard Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-page Admin Dashboard (`frontend/admin/index.html`) using Alpine.js + Tailwind CSS CDN, served by FastAPI at `/dashboard`, with five functional tabs that call the existing admin REST API.

**Architecture:** Single HTML file with Alpine.js `adminApp()` managing auth state, tab switching, and all API calls. JWT stored in `localStorage`. FastAPI mounts `frontend/admin/` as StaticFiles at `/dashboard`. Each tab section is populated in a dedicated task.

**Tech Stack:** Alpine.js v3 (CDN), Tailwind CSS v3 (CDN play), HTML5, existing FastAPI admin REST API.

## Global Constraints

- No build step — plain HTML + CDN-loaded libraries only
- JWT stored as `nail_admin_token` in `localStorage`; HTTP helper auto-attaches `Authorization: Bearer <token>`; 401/403 triggers logout
- Admin REST API prefix: `/admin` — POST `/admin/login` for auth, all others require bearer token
- Mount point: `/dashboard` (no trailing-slash issue — StaticFiles with `html=True` serves `index.html`)
- Brand colors: bg `#F4EDE5`, text `#241914`, accent rose `#B86E78`, gold `#A6864F`
- Five tabs: Studio Profile, Services, Portfolio, Appointments, Schedule — in that order
- `admin_username` default `"admin"` — pre-fill login form username
- Python 3.12, FastAPI, all existing patterns from `app/main.py` (conditional static mount like LIFF)
- `ADMIN_JWT_SECRET` must be set before importing `app.main` in any test

---

### Task 1: Shell + Login + Static Serving

**Files:**
- Create: `frontend/admin/index.html`
- Modify: `app/main.py` (add static mount after LIFF mount)
- Create: `tests/test_admin_ui.py`

**Interfaces:**
- Produces: `adminApp()` JS function with auth, tab switching, API helper, and stub methods for all five tabs
- Produces: `/dashboard/` route serving `index.html`

- [ ] **Step 1: Add static mount to `app/main.py`**

In `create_app()`, add after the existing LIFF mount block (after line `if _liff_dist.exists(): ...`):

```python
    _admin_ui = Path(__file__).parent.parent / "frontend" / "admin"
    if _admin_ui.exists():
        app.mount("/dashboard", StaticFiles(directory=_admin_ui, html=True), name="admin_ui")
```

`StaticFiles` is already imported. No new imports needed.

- [ ] **Step 2: Write failing test**

Create `tests/test_admin_ui.py`:

```python
import os
os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")

from fastapi.testclient import TestClient
from app.main import app


def test_dashboard_serves_html():
    client = TestClient(app)
    res = client.get("/dashboard/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "adminApp" in res.text


def test_dashboard_contains_tab_ids():
    client = TestClient(app)
    res = client.get("/dashboard/")
    assert res.status_code == 200
    for tab in ["studio", "services", "portfolio", "appointments", "schedule"]:
        assert tab in res.text
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd /Users/maxim/Documents/dev/nail-bot
pytest tests/test_admin_ui.py -v
```

Expected: FAIL — `frontend/admin/` does not exist yet, so mount is skipped and `/dashboard/` returns 404.

- [ ] **Step 4: Create `frontend/admin/index.html`**

```bash
mkdir -p frontend/admin
```

Create `frontend/admin/index.html` with this exact content:

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Hualienvibe — Admin</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
  <style>
    [x-cloak] { display: none !important; }
    body { background-color: #F4EDE5; color: #241914; }
  </style>
  <script>
    tailwind.config = {
      theme: { extend: { colors: {
        rose: '#B86E78', gold: '#A6864F', cream: '#F4EDE5', ink: '#241914'
      }}}
    }
  </script>
</head>
<body x-data="adminApp()" x-init="init()" x-cloak class="min-h-screen font-sans">

  <!-- ── Login overlay ─────────────────────────────────────────────────── -->
  <div x-show="!token" class="fixed inset-0 flex items-center justify-center bg-[#F4EDE5]">
    <div class="w-full max-w-sm bg-white rounded-2xl shadow-lg p-8">
      <h1 class="text-2xl font-bold text-[#241914] mb-6 text-center">💅 Hualienvibe Admin</h1>
      <form @submit.prevent="login()">
        <div class="mb-4">
          <label class="block text-sm font-medium text-[#241914] mb-1">Username</label>
          <input type="text" x-model="loginForm.username" required autocomplete="username"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-[#B86E78]" />
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium text-[#241914] mb-1">Password</label>
          <input type="password" x-model="loginForm.password" required autocomplete="current-password"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-[#B86E78]" />
        </div>
        <p x-show="loginError" x-text="loginError" class="text-red-600 text-sm mb-3"></p>
        <button type="submit" :disabled="loginLoading"
          class="w-full bg-[#B86E78] text-white rounded-lg py-2 font-medium hover:bg-[#a5606a] disabled:opacity-50">
          <span x-show="!loginLoading">Sign In</span>
          <span x-show="loginLoading">Signing in…</span>
        </button>
      </form>
    </div>
  </div>

  <!-- ── Dashboard shell ──────────────────────────────────────────────── -->
  <div x-show="token" class="flex h-screen">

    <!-- Sidebar -->
    <aside class="w-52 bg-[#241914] text-white flex flex-col shrink-0">
      <div class="p-6 border-b border-white/10">
        <h1 class="text-lg font-bold">💅 Admin</h1>
      </div>
      <nav class="flex-1 p-4 space-y-1">
        <template x-for="tab in tabs" :key="tab.id">
          <button @click="switchTab(tab.id)"
            :class="currentTab === tab.id ? 'bg-[#B86E78] text-white' : 'text-white/70 hover:bg-white/10'"
            class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors">
            <span x-text="tab.icon + ' ' + tab.label"></span>
          </button>
        </template>
      </nav>
      <div class="p-4 border-t border-white/10">
        <button @click="logout()" class="text-white/60 text-sm hover:text-white">Sign out</button>
      </div>
    </aside>

    <!-- Main content -->
    <main class="flex-1 overflow-auto p-8">

      <!-- TAB:STUDIO:START -->
      <div x-show="currentTab === 'studio'">
        <p class="text-gray-400 text-sm">Studio Profile — coming in Task 2</p>
      </div>
      <!-- TAB:STUDIO:END -->

      <!-- TAB:SERVICES:START -->
      <div x-show="currentTab === 'services'">
        <p class="text-gray-400 text-sm">Services — coming in Task 3</p>
      </div>
      <!-- TAB:SERVICES:END -->

      <!-- TAB:PORTFOLIO:START -->
      <div x-show="currentTab === 'portfolio'">
        <p class="text-gray-400 text-sm">Portfolio — coming in Task 4</p>
      </div>
      <!-- TAB:PORTFOLIO:END -->

      <!-- TAB:APPOINTMENTS:START -->
      <div x-show="currentTab === 'appointments'">
        <p class="text-gray-400 text-sm">Appointments — coming in Task 5</p>
      </div>
      <!-- TAB:APPOINTMENTS:END -->

      <!-- TAB:SCHEDULE:START -->
      <div x-show="currentTab === 'schedule'">
        <p class="text-gray-400 text-sm">Schedule — coming in Task 6</p>
      </div>
      <!-- TAB:SCHEDULE:END -->

    </main>
  </div>

<script>
function adminApp() {
  return {
    // ── Auth ──────────────────────────────────────────────────────────────
    token: localStorage.getItem('nail_admin_token') || '',
    loginForm: { username: 'admin', password: '' },
    loginError: '',
    loginLoading: false,

    // ── Navigation ────────────────────────────────────────────────────────
    currentTab: 'studio',
    tabs: [
      { id: 'studio',       icon: '🏠', label: 'Studio Profile' },
      { id: 'services',     icon: '💅', label: 'Services' },
      { id: 'portfolio',    icon: '🖼️',  label: 'Portfolio' },
      { id: 'appointments', icon: '📅', label: 'Appointments' },
      { id: 'schedule',     icon: '🗓️',  label: 'Schedule' },
    ],

    // ── HTTP helper ───────────────────────────────────────────────────────
    // Auto-attaches bearer token. Logs out on 401/403. Returns Response or null.
    async api(path, options = {}) {
      const res = await fetch(path, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`,
          ...(options.headers || {}),
        },
      });
      if (res.status === 401 || res.status === 403) { this.logout(); return null; }
      return res;
    },

    async login() {
      this.loginLoading = true;
      this.loginError = '';
      try {
        const res = await fetch('/admin/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.loginForm),
        });
        if (res.ok) {
          const data = await res.json();
          this.token = data.access_token;
          localStorage.setItem('nail_admin_token', this.token);
          await this.loadTab(this.currentTab);
        } else {
          this.loginError = 'Invalid username or password';
        }
      } finally {
        this.loginLoading = false;
      }
    },

    logout() {
      this.token = '';
      localStorage.removeItem('nail_admin_token');
    },

    async switchTab(tab) {
      this.currentTab = tab;
      await this.loadTab(tab);
    },

    async loadTab(tab) {
      if      (tab === 'studio')       await this.loadStudio();
      else if (tab === 'services')     await this.loadServices();
      else if (tab === 'portfolio')    await this.loadPortfolio();
      else if (tab === 'appointments') await this.loadAppointments();
      else if (tab === 'schedule')     await this.loadSchedule();
    },

    async init() {
      if (this.token) await this.loadTab(this.currentTab);
    },

    // ── Studio Profile ────────────────────────────────────────────────────
    studio: {
      studio_name: '', owner_name: '', address: '', phone: '', instagram: '',
      cancellation_policy: '', aftercare_notes: '', ai_persona_notes: '', owner_line_user_id: '',
    },
    studioSaving: false,
    studioMsg: '',

    async loadStudio() { /* STUB:loadStudio */ },
    async saveStudio() { /* STUB:saveStudio */ },

    // ── Services ──────────────────────────────────────────────────────────
    services: [],
    showServiceForm: false,
    editingServiceId: null,
    serviceForm: {
      name: '', name_en: '', name_tl: '', name_id: '', name_vi: '',
      description: '', agent_notes: '', duration_min: 60, price: 0,
      image_url: '', category: 'general', is_available: true, in_carousel: false, sort_order: 0,
    },
    serviceMsg: '',

    async loadServices() { /* STUB:loadServices */ },
    openNewServiceForm() { /* STUB:openNewServiceForm */ },
    openEditServiceForm(_svc) { /* STUB:openEditServiceForm */ },
    async saveService() { /* STUB:saveService */ },
    async toggleServiceField(_svc, _field) { /* STUB:toggleServiceField */ },
    async deleteService(_id) { /* STUB:deleteService */ },

    // ── Portfolio ─────────────────────────────────────────────────────────
    portfolio: [],
    showPortfolioForm: false,
    editingPortfolioId: null,
    portfolioForm: { title: '', image_url: '', service_id: '', sort_order: 0, is_visible: true },
    portfolioMsg: '',

    async loadPortfolio() { /* STUB:loadPortfolio */ },
    openNewPortfolioForm() { /* STUB:openNewPortfolioForm */ },
    openEditPortfolioForm(_item) { /* STUB:openEditPortfolioForm */ },
    async savePortfolioItem() { /* STUB:savePortfolioItem */ },
    async togglePortfolioVisibility(_item) { /* STUB:togglePortfolioVisibility */ },
    async deletePortfolioItem(_id) { /* STUB:deletePortfolioItem */ },

    // ── Appointments ──────────────────────────────────────────────────────
    appointments: [],
    apptFilter: { status: '', from_date: '', to_date: '' },
    apptMsg: '',

    async loadAppointments() { /* STUB:loadAppointments */ },
    async updateApptStatus(_appt, _status) { /* STUB:updateApptStatus */ },

    // ── Schedule ──────────────────────────────────────────────────────────
    weeklyTemplate: [],
    dateOverrides: [],
    overrideForm: { date: '', is_blocked: true, custom_start: '', custom_end: '' },
    showOverrideForm: false,
    scheduleMsg: '',

    async loadSchedule() { /* STUB:loadSchedule */ },
    async saveWeeklyDay(_day) { /* STUB:saveWeeklyDay */ },
    async saveOverride() { /* STUB:saveOverride */ },
    async deleteOverride(_date) { /* STUB:deleteOverride */ },
  };
}
</script>
</body>
</html>
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_admin_ui.py -v
```

Expected: 2 PASSED. The file exists, mount activates, `/dashboard/` serves `index.html`.

- [ ] **Step 6: Run full suite to check nothing broke**

```bash
pytest --tb=short -q
```

Expected: all existing 117 tests still pass + 2 new = 119 total.

- [ ] **Step 7: Commit**

```bash
git add frontend/admin/index.html app/main.py tests/test_admin_ui.py
git commit -m "feat: admin dashboard shell — login, tab nav, static serving at /dashboard"
```

---

### Task 2: Studio Profile Tab

**Files:**
- Modify: `frontend/admin/index.html` — replace `TAB:STUDIO` placeholder HTML + replace studio JS stubs

**Interfaces:**
- Consumes: `GET /admin/studio` → `StudioProfileOut` (all fields nullable except `studio_name`); 404 if no row yet
- Consumes: `PUT /admin/studio` body `StudioProfileIn` → `StudioProfileOut`
- Consumes: `this.api(path, options)` helper from Task 1

- [ ] **Step 1: Replace the Studio Profile HTML placeholder**

In `frontend/admin/index.html`, find and replace:

```
      <!-- TAB:STUDIO:START -->
      <div x-show="currentTab === 'studio'">
        <p class="text-gray-400 text-sm">Studio Profile — coming in Task 2</p>
      </div>
      <!-- TAB:STUDIO:END -->
```

Replace with:

```
      <!-- TAB:STUDIO:START -->
      <div x-show="currentTab === 'studio'">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-[#241914]">Studio Profile</h2>
          <span x-show="studioMsg" x-text="studioMsg"
            class="text-green-700 text-sm bg-green-50 px-3 py-1 rounded-full"></span>
        </div>
        <div class="bg-white rounded-2xl shadow-sm p-6 max-w-2xl">
          <div class="grid grid-cols-1 gap-4">
            <div>
              <label class="block text-sm font-medium text-[#241914] mb-1">Studio Name *</label>
              <input type="text" x-model="studio.studio_name" required
                class="w-full border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#B86E78]" />
            </div>
            <div>
              <label class="block text-sm font-medium text-[#241914] mb-1">Owner Name</label>
              <input type="text" x-model="studio.owner_name"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#B86E78]" />
            </div>
            <div>
              <label class="block text-sm font-medium text-[#241914] mb-1">Address</label>
              <input type="text" x-model="studio.address"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#B86E78]" />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-[#241914] mb-1">Phone</label>
                <input type="text" x-model="studio.phone"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div>
                <label class="block text-sm font-medium text-[#241914] mb-1">Instagram</label>
                <input type="text" x-model="studio.instagram" placeholder="@handle"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#B86E78]" />
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-[#241914] mb-1">Owner LINE User ID</label>
              <input type="text" x-model="studio.owner_line_user_id" placeholder="Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#B86E78]" />
            </div>
            <div>
              <label class="block text-sm font-medium text-[#241914] mb-1">Cancellation Policy</label>
              <textarea x-model="studio.cancellation_policy" rows="3"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#B86E78]"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-[#241914] mb-1">Aftercare Notes</label>
              <textarea x-model="studio.aftercare_notes" rows="3"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#B86E78]"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-[#241914] mb-1">AI Persona Notes</label>
              <p class="text-xs text-gray-400 mb-1">Free-form instructions for the booking assistant's tone</p>
              <textarea x-model="studio.ai_persona_notes" rows="4"
                class="w-full border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#B86E78]"></textarea>
            </div>
          </div>
          <div class="mt-6 flex justify-end">
            <button @click="saveStudio()" :disabled="studioSaving"
              class="bg-[#B86E78] text-white px-6 py-2 rounded-lg font-medium hover:bg-[#a5606a] disabled:opacity-50">
              <span x-show="!studioSaving">Save</span>
              <span x-show="studioSaving">Saving…</span>
            </button>
          </div>
        </div>
      </div>
      <!-- TAB:STUDIO:END -->
```

- [ ] **Step 2: Replace the studio JS stubs**

Find and replace:

```
    async loadStudio() { /* STUB:loadStudio */ },
    async saveStudio() { /* STUB:saveStudio */ },
```

Replace with:

```
    async loadStudio() {
      const res = await this.api('/admin/studio');
      if (!res) return;
      if (res.ok) this.studio = await res.json();
      // 404 = no studio row yet; form stays at defaults
    },
    async saveStudio() {
      this.studioSaving = true;
      const res = await this.api('/admin/studio', {
        method: 'PUT',
        body: JSON.stringify(this.studio),
      });
      this.studioSaving = false;
      if (res && res.ok) {
        this.studioMsg = '✓ Saved';
        setTimeout(() => { this.studioMsg = ''; }, 2500);
      }
    },
```

- [ ] **Step 3: Verify manually**

```bash
cd /Users/maxim/Documents/dev/nail-bot
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/dashboard/` in browser. Log in (you need a real `ADMIN_PASSWORD_HASH` or set one in `.env`; for quick testing set `ADMIN_PASSWORD_HASH` to the bcrypt hash of "test": `$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW`). Verify: Studio Profile tab shows all fields, save button works, success message appears.

- [ ] **Step 4: Run full test suite**

```bash
pytest --tb=short -q
```

Expected: 119 tests still pass (no new Python tests in this task).

- [ ] **Step 5: Commit**

```bash
git add frontend/admin/index.html
git commit -m "feat: admin dashboard — studio profile tab"
```

---

### Task 3: Services Tab

**Files:**
- Modify: `frontend/admin/index.html` — replace `TAB:SERVICES` placeholder HTML + replace services JS stubs

**Interfaces:**
- Consumes: `GET /admin/services` → `list[AdminServiceOut]`
- Consumes: `POST /admin/services` body `AdminServiceIn` → `AdminServiceOut` (201)
- Consumes: `PUT /admin/services/{id}` body `AdminServiceIn` → `AdminServiceOut`
- Consumes: `DELETE /admin/services/{id}` → 204; 409 if FK-constrained
- `AdminServiceIn` fields: `name`, `name_en`, `name_tl`, `name_id`, `name_vi`, `description`, `agent_notes`, `duration_min` (int), `price` (int), `image_url` (str|null), `category` (str), `is_available` (bool), `in_carousel` (bool), `sort_order` (int)

- [ ] **Step 1: Replace Services HTML placeholder**

Find and replace:

```
      <!-- TAB:SERVICES:START -->
      <div x-show="currentTab === 'services'">
        <p class="text-gray-400 text-sm">Services — coming in Task 3</p>
      </div>
      <!-- TAB:SERVICES:END -->
```

Replace with:

```
      <!-- TAB:SERVICES:START -->
      <div x-show="currentTab === 'services'">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-[#241914]">Services</h2>
          <button @click="openNewServiceForm()"
            class="bg-[#B86E78] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#a5606a]">
            + New Service
          </button>
        </div>

        <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
          <table class="w-full text-sm">
            <thead class="bg-[#F4EDE5]">
              <tr>
                <th class="px-4 py-3 text-left font-medium text-[#241914]">Name (zh)</th>
                <th class="px-4 py-3 text-left font-medium text-[#241914]">Duration</th>
                <th class="px-4 py-3 text-left font-medium text-[#241914]">Price</th>
                <th class="px-4 py-3 text-left font-medium text-[#241914]">Category</th>
                <th class="px-4 py-3 text-center font-medium text-[#241914]">Available</th>
                <th class="px-4 py-3 text-center font-medium text-[#241914]">Carousel</th>
                <th class="px-4 py-3 text-right font-medium text-[#241914]">Actions</th>
              </tr>
            </thead>
            <tbody>
              <template x-for="svc in services" :key="svc.id">
                <tr class="border-t border-gray-100 hover:bg-gray-50">
                  <td class="px-4 py-3 font-medium" x-text="svc.name"></td>
                  <td class="px-4 py-3" x-text="svc.duration_min + ' min'"></td>
                  <td class="px-4 py-3" x-text="'NT$' + svc.price"></td>
                  <td class="px-4 py-3 text-gray-500" x-text="svc.category"></td>
                  <td class="px-4 py-3 text-center">
                    <button @click="toggleServiceField(svc, 'is_available')"
                      :class="svc.is_available ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
                      class="px-2 py-0.5 rounded text-xs font-medium">
                      <span x-text="svc.is_available ? 'Yes' : 'No'"></span>
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button @click="toggleServiceField(svc, 'in_carousel')"
                      :class="svc.in_carousel ? 'bg-[#B86E78]/20 text-[#B86E78]' : 'bg-gray-100 text-gray-500'"
                      class="px-2 py-0.5 rounded text-xs font-medium">
                      <span x-text="svc.in_carousel ? 'Yes' : 'No'"></span>
                    </button>
                  </td>
                  <td class="px-4 py-3 text-right space-x-2">
                    <button @click="openEditServiceForm(svc)" class="text-[#A6864F] hover:underline text-xs">Edit</button>
                    <button @click="deleteService(svc.id)" class="text-red-500 hover:underline text-xs">Delete</button>
                  </td>
                </tr>
              </template>
              <tr x-show="services.length === 0">
                <td colspan="7" class="px-4 py-8 text-center text-gray-400">No services yet</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p x-show="serviceMsg" x-text="serviceMsg" class="mt-3 text-sm text-red-600"></p>

        <!-- Service modal -->
        <div x-show="showServiceForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div class="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6">
            <h3 class="text-lg font-bold text-[#241914] mb-4"
              x-text="editingServiceId ? 'Edit Service' : 'New Service'"></h3>
            <div class="grid grid-cols-2 gap-4">
              <div class="col-span-2">
                <label class="block text-xs font-medium text-gray-700 mb-1">Name (Chinese) *</label>
                <input type="text" x-model="serviceForm.name" required
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Name (English)</label>
                <input type="text" x-model="serviceForm.name_en"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Name (Filipino / Tagalog)</label>
                <input type="text" x-model="serviceForm.name_tl"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Name (Indonesian)</label>
                <input type="text" x-model="serviceForm.name_id"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Name (Vietnamese)</label>
                <input type="text" x-model="serviceForm.name_vi"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Duration (min) *</label>
                <input type="number" x-model.number="serviceForm.duration_min" min="15" required
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Price (NTD) *</label>
                <input type="number" x-model.number="serviceForm.price" min="0" required
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Category</label>
                <input type="text" x-model="serviceForm.category" placeholder="general"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Sort Order</label>
                <input type="number" x-model.number="serviceForm.sort_order"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div class="col-span-2">
                <label class="block text-xs font-medium text-gray-700 mb-1">Image URL</label>
                <input type="url" x-model="serviceForm.image_url"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div class="col-span-2">
                <label class="block text-xs font-medium text-gray-700 mb-1">Description (Chinese)</label>
                <textarea x-model="serviceForm.description" rows="2"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]"></textarea>
              </div>
              <div class="col-span-2">
                <label class="block text-xs font-medium text-gray-700 mb-1">Agent Notes <span class="text-gray-400">(internal — not shown to customers)</span></label>
                <textarea x-model="serviceForm.agent_notes" rows="2"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]"></textarea>
              </div>
              <div class="flex items-center gap-2">
                <input type="checkbox" x-model="serviceForm.is_available" id="svc_available"
                  class="rounded border-gray-300" />
                <label for="svc_available" class="text-xs font-medium text-gray-700">Available to book</label>
              </div>
              <div class="flex items-center gap-2">
                <input type="checkbox" x-model="serviceForm.in_carousel" id="svc_carousel"
                  class="rounded border-gray-300" />
                <label for="svc_carousel" class="text-xs font-medium text-gray-700">Show in LINE carousel</label>
              </div>
            </div>
            <div class="mt-6 flex justify-end gap-3">
              <button @click="showServiceForm = false; editingServiceId = null"
                class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancel</button>
              <button @click="saveService()"
                class="bg-[#B86E78] text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-[#a5606a]">
                <span x-text="editingServiceId ? 'Update' : 'Create'"></span>
              </button>
            </div>
          </div>
        </div>
      </div>
      <!-- TAB:SERVICES:END -->
```

- [ ] **Step 2: Replace all services JS stubs**

Find and replace the entire services stubs block:

```
    async loadServices() { /* STUB:loadServices */ },
    openNewServiceForm() { /* STUB:openNewServiceForm */ },
    openEditServiceForm(_svc) { /* STUB:openEditServiceForm */ },
    async saveService() { /* STUB:saveService */ },
    async toggleServiceField(_svc, _field) { /* STUB:toggleServiceField */ },
    async deleteService(_id) { /* STUB:deleteService */ },
```

Replace with:

```
    async loadServices() {
      const res = await this.api('/admin/services');
      if (res && res.ok) this.services = await res.json();
    },
    openNewServiceForm() {
      this.editingServiceId = null;
      this.serviceForm = {
        name: '', name_en: '', name_tl: '', name_id: '', name_vi: '',
        description: '', agent_notes: '', duration_min: 60, price: 0,
        image_url: '', category: 'general', is_available: true, in_carousel: false, sort_order: 0,
      };
      this.showServiceForm = true;
    },
    openEditServiceForm(svc) {
      this.editingServiceId = svc.id;
      this.serviceForm = {
        name: svc.name, name_en: svc.name_en, name_tl: svc.name_tl,
        name_id: svc.name_id, name_vi: svc.name_vi, description: svc.description,
        agent_notes: svc.agent_notes, duration_min: svc.duration_min, price: svc.price,
        image_url: svc.image_url || '', category: svc.category,
        is_available: svc.is_available, in_carousel: svc.in_carousel, sort_order: svc.sort_order,
      };
      this.showServiceForm = true;
    },
    async saveService() {
      const url = this.editingServiceId
        ? `/admin/services/${this.editingServiceId}` : '/admin/services';
      const method = this.editingServiceId ? 'PUT' : 'POST';
      const body = { ...this.serviceForm, image_url: this.serviceForm.image_url || null };
      const res = await this.api(url, { method, body: JSON.stringify(body) });
      if (res && res.ok) {
        await this.loadServices();
        this.showServiceForm = false;
        this.editingServiceId = null;
      }
    },
    async toggleServiceField(svc, field) {
      const body = {
        name: svc.name, name_en: svc.name_en, name_tl: svc.name_tl,
        name_id: svc.name_id, name_vi: svc.name_vi, description: svc.description,
        agent_notes: svc.agent_notes, duration_min: svc.duration_min, price: svc.price,
        image_url: svc.image_url || null, category: svc.category,
        is_available: svc.is_available, in_carousel: svc.in_carousel, sort_order: svc.sort_order,
        [field]: !svc[field],
      };
      const res = await this.api(`/admin/services/${svc.id}`, { method: 'PUT', body: JSON.stringify(body) });
      if (res && res.ok) svc[field] = !svc[field];
    },
    async deleteService(id) {
      if (!confirm('Delete this service?')) return;
      const res = await this.api(`/admin/services/${id}`, { method: 'DELETE' });
      if (!res) return;
      if (res.status === 409) {
        this.serviceMsg = 'Cannot delete — service has existing appointments';
        setTimeout(() => { this.serviceMsg = ''; }, 4000);
        return;
      }
      if (res.ok || res.status === 204) this.services = this.services.filter(s => s.id !== id);
    },
```

- [ ] **Step 3: Run full suite + manual verify**

```bash
pytest --tb=short -q
```

Expected: 119 tests pass. Start dev server and verify services tab: create a service, toggle is_available, delete it.

- [ ] **Step 4: Commit**

```bash
git add frontend/admin/index.html
git commit -m "feat: admin dashboard — services tab (CRUD + toggles)"
```

---

### Task 4: Portfolio Tab

**Files:**
- Modify: `frontend/admin/index.html` — replace `TAB:PORTFOLIO` placeholder + portfolio JS stubs

**Interfaces:**
- Consumes: `GET /admin/portfolio` → `list[AdminPortfolioOut]`
- Consumes: `POST /admin/portfolio` body `AdminPortfolioIn` → `AdminPortfolioOut` (201)
- Consumes: `PUT /admin/portfolio/{id}` body `AdminPortfolioIn` → `AdminPortfolioOut`
- Consumes: `DELETE /admin/portfolio/{id}` → 204
- `AdminPortfolioIn` fields: `title` (str), `image_url` (str), `service_id` (UUID|null), `sort_order` (int), `is_visible` (bool)
- Consumes: `this.services` (already loaded from services tab — call `loadServices()` if empty)

- [ ] **Step 1: Replace Portfolio HTML placeholder**

Find and replace:

```
      <!-- TAB:PORTFOLIO:START -->
      <div x-show="currentTab === 'portfolio'">
        <p class="text-gray-400 text-sm">Portfolio — coming in Task 4</p>
      </div>
      <!-- TAB:PORTFOLIO:END -->
```

Replace with:

```
      <!-- TAB:PORTFOLIO:START -->
      <div x-show="currentTab === 'portfolio'">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-[#241914]">Portfolio</h2>
          <button @click="openNewPortfolioForm()"
            class="bg-[#B86E78] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#a5606a]">
            + Add Photo
          </button>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          <template x-for="item in portfolio" :key="item.id">
            <div class="bg-white rounded-xl shadow-sm overflow-hidden">
              <div class="relative aspect-square bg-gray-100">
                <img :src="item.image_url" :alt="item.title"
                  class="w-full h-full object-cover"
                  @error="$event.target.style.display='none'" />
                <div x-show="!item.is_visible"
                  class="absolute inset-0 bg-black/40 flex items-center justify-center">
                  <span class="text-white text-xs font-semibold bg-black/50 px-2 py-1 rounded">Hidden</span>
                </div>
              </div>
              <div class="p-3">
                <p class="font-medium text-sm text-[#241914] truncate" x-text="item.title"></p>
                <p class="text-xs text-gray-400 mt-0.5" x-text="'#' + item.sort_order"></p>
                <div class="flex gap-3 mt-2">
                  <button @click="openEditPortfolioForm(item)" class="text-xs text-[#A6864F] hover:underline">Edit</button>
                  <button @click="togglePortfolioVisibility(item)" class="text-xs text-gray-500 hover:underline"
                    x-text="item.is_visible ? 'Hide' : 'Show'"></button>
                  <button @click="deletePortfolioItem(item.id)" class="text-xs text-red-500 hover:underline">Delete</button>
                </div>
              </div>
            </div>
          </template>
          <div x-show="portfolio.length === 0" class="col-span-full py-12 text-center text-gray-400">
            No portfolio items yet
          </div>
        </div>
        <p x-show="portfolioMsg" x-text="portfolioMsg" class="mt-3 text-sm text-red-600"></p>

        <!-- Portfolio form modal -->
        <div x-show="showPortfolioForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h3 class="text-lg font-bold text-[#241914] mb-4"
              x-text="editingPortfolioId ? 'Edit Item' : 'Add Photo'"></h3>
            <div class="space-y-4">
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Title *</label>
                <input type="text" x-model="portfolioForm.title" required
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Image URL *</label>
                <input type="url" x-model="portfolioForm.image_url" required
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Linked Service</label>
                <select x-model="portfolioForm.service_id"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]">
                  <option value="">None</option>
                  <template x-for="svc in services" :key="svc.id">
                    <option :value="svc.id" x-text="svc.name"></option>
                  </template>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Sort Order</label>
                <input type="number" x-model.number="portfolioForm.sort_order"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div class="flex items-center gap-2">
                <input type="checkbox" x-model="portfolioForm.is_visible" id="pf_visible"
                  class="rounded border-gray-300" />
                <label for="pf_visible" class="text-xs font-medium text-gray-700">Visible in gallery</label>
              </div>
            </div>
            <div class="mt-6 flex justify-end gap-3">
              <button @click="showPortfolioForm = false; editingPortfolioId = null"
                class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancel</button>
              <button @click="savePortfolioItem()"
                class="bg-[#B86E78] text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-[#a5606a]">
                <span x-text="editingPortfolioId ? 'Update' : 'Add'"></span>
              </button>
            </div>
          </div>
        </div>
      </div>
      <!-- TAB:PORTFOLIO:END -->
```

- [ ] **Step 2: Replace portfolio JS stubs**

Find and replace:

```
    async loadPortfolio() { /* STUB:loadPortfolio */ },
    openNewPortfolioForm() { /* STUB:openNewPortfolioForm */ },
    openEditPortfolioForm(_item) { /* STUB:openEditPortfolioForm */ },
    async savePortfolioItem() { /* STUB:savePortfolioItem */ },
    async togglePortfolioVisibility(_item) { /* STUB:togglePortfolioVisibility */ },
    async deletePortfolioItem(_id) { /* STUB:deletePortfolioItem */ },
```

Replace with:

```
    async loadPortfolio() {
      if (this.services.length === 0) await this.loadServices();
      const res = await this.api('/admin/portfolio');
      if (res && res.ok) this.portfolio = await res.json();
    },
    openNewPortfolioForm() {
      this.editingPortfolioId = null;
      this.portfolioForm = { title: '', image_url: '', service_id: '', sort_order: 0, is_visible: true };
      this.showPortfolioForm = true;
    },
    openEditPortfolioForm(item) {
      this.editingPortfolioId = item.id;
      this.portfolioForm = {
        title: item.title, image_url: item.image_url,
        service_id: item.service_id || '', sort_order: item.sort_order, is_visible: item.is_visible,
      };
      this.showPortfolioForm = true;
    },
    async savePortfolioItem() {
      const body = {
        ...this.portfolioForm,
        service_id: this.portfolioForm.service_id || null,
      };
      const url = this.editingPortfolioId
        ? `/admin/portfolio/${this.editingPortfolioId}` : '/admin/portfolio';
      const method = this.editingPortfolioId ? 'PUT' : 'POST';
      const res = await this.api(url, { method, body: JSON.stringify(body) });
      if (res && res.ok) {
        await this.loadPortfolio();
        this.showPortfolioForm = false;
        this.editingPortfolioId = null;
      }
    },
    async togglePortfolioVisibility(item) {
      const body = {
        title: item.title, image_url: item.image_url,
        service_id: item.service_id || null,
        sort_order: item.sort_order, is_visible: !item.is_visible,
      };
      const res = await this.api(`/admin/portfolio/${item.id}`, { method: 'PUT', body: JSON.stringify(body) });
      if (res && res.ok) item.is_visible = !item.is_visible;
    },
    async deletePortfolioItem(id) {
      if (!confirm('Delete this portfolio item?')) return;
      const res = await this.api(`/admin/portfolio/${id}`, { method: 'DELETE' });
      if (res && (res.ok || res.status === 204))
        this.portfolio = this.portfolio.filter(p => p.id !== id);
    },
```

- [ ] **Step 3: Run full suite + manual verify**

```bash
pytest --tb=short -q
```

Expected: 119 pass. Start dev server and verify portfolio tab: add an item with a valid image URL, toggle visibility, delete.

- [ ] **Step 4: Commit**

```bash
git add frontend/admin/index.html
git commit -m "feat: admin dashboard — portfolio tab (grid + CRUD)"
```

---

### Task 5: Appointments Tab

**Files:**
- Modify: `frontend/admin/index.html` — replace `TAB:APPOINTMENTS` placeholder + appointments JS stubs

**Interfaces:**
- Consumes: `GET /admin/appointments?status=&from_date=YYYY-MM-DD&to_date=YYYY-MM-DD` → `list[AdminAppointmentOut]`
- `AdminAppointmentOut` fields: `id`, `line_user_id`, `service_name`, `scheduled_at` (ISO datetime with tz), `duration_min`, `status` (`confirmed`|`completed`|`cancelled`), `customer_name`, `notes`
- Consumes: `PUT /admin/appointments/{id}` body `{ "status": "completed"|"cancelled" }` → `AdminAppointmentOut`

- [ ] **Step 1: Replace Appointments HTML placeholder**

Find and replace:

```
      <!-- TAB:APPOINTMENTS:START -->
      <div x-show="currentTab === 'appointments'">
        <p class="text-gray-400 text-sm">Appointments — coming in Task 5</p>
      </div>
      <!-- TAB:APPOINTMENTS:END -->
```

Replace with:

```
      <!-- TAB:APPOINTMENTS:START -->
      <div x-show="currentTab === 'appointments'">
        <h2 class="text-2xl font-bold text-[#241914] mb-6">Appointments</h2>

        <!-- Filters -->
        <div class="bg-white rounded-xl shadow-sm p-4 mb-4 flex flex-wrap gap-4 items-end">
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Status</label>
            <select x-model="apptFilter.status" @change="loadAppointments()"
              class="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]">
              <option value="">All</option>
              <option value="confirmed">Confirmed</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">From</label>
            <input type="date" x-model="apptFilter.from_date" @change="loadAppointments()"
              class="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">To</label>
            <input type="date" x-model="apptFilter.to_date" @change="loadAppointments()"
              class="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
          </div>
          <button @click="apptFilter = { status: '', from_date: '', to_date: '' }; loadAppointments()"
            class="px-3 py-2 text-sm text-gray-500 hover:text-gray-700">Clear</button>
        </div>

        <!-- Table -->
        <div class="bg-white rounded-2xl shadow-sm overflow-x-auto">
          <table class="w-full text-sm whitespace-nowrap">
            <thead class="bg-[#F4EDE5]">
              <tr>
                <th class="px-4 py-3 text-left font-medium text-[#241914]">Date & Time</th>
                <th class="px-4 py-3 text-left font-medium text-[#241914]">Customer</th>
                <th class="px-4 py-3 text-left font-medium text-[#241914]">Service</th>
                <th class="px-4 py-3 text-left font-medium text-[#241914]">Notes</th>
                <th class="px-4 py-3 text-left font-medium text-[#241914]">Status</th>
                <th class="px-4 py-3 text-right font-medium text-[#241914]">Actions</th>
              </tr>
            </thead>
            <tbody>
              <template x-for="appt in appointments" :key="appt.id">
                <tr class="border-t border-gray-100 hover:bg-gray-50">
                  <td class="px-4 py-3 text-[#241914]"
                    x-text="new Date(appt.scheduled_at).toLocaleString('zh-TW', {timeZone:'Asia/Taipei', month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'})"></td>
                  <td class="px-4 py-3 font-medium" x-text="appt.customer_name"></td>
                  <td class="px-4 py-3" x-text="appt.service_name"></td>
                  <td class="px-4 py-3 text-gray-400 text-xs max-w-xs truncate" x-text="appt.notes || '—'"></td>
                  <td class="px-4 py-3">
                    <span :class="{
                        'bg-blue-100 text-blue-700':   appt.status === 'confirmed',
                        'bg-green-100 text-green-700': appt.status === 'completed',
                        'bg-red-100 text-red-600':     appt.status === 'cancelled',
                      }"
                      class="px-2 py-0.5 rounded text-xs font-medium" x-text="appt.status"></span>
                  </td>
                  <td class="px-4 py-3 text-right space-x-2">
                    <button x-show="appt.status === 'confirmed'"
                      @click="updateApptStatus(appt, 'completed')"
                      class="text-xs text-green-700 hover:underline">Complete</button>
                    <button x-show="appt.status === 'confirmed'"
                      @click="updateApptStatus(appt, 'cancelled')"
                      class="text-xs text-red-500 hover:underline">Cancel</button>
                  </td>
                </tr>
              </template>
              <tr x-show="appointments.length === 0">
                <td colspan="6" class="px-4 py-8 text-center text-gray-400">No appointments found</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p x-show="apptMsg" x-text="apptMsg" class="mt-3 text-sm text-green-700"></p>
      </div>
      <!-- TAB:APPOINTMENTS:END -->
```

- [ ] **Step 2: Replace appointments JS stubs**

Find and replace:

```
    async loadAppointments() { /* STUB:loadAppointments */ },
    async updateApptStatus(_appt, _status) { /* STUB:updateApptStatus */ },
```

Replace with:

```
    async loadAppointments() {
      const params = new URLSearchParams();
      if (this.apptFilter.status)    params.set('status',    this.apptFilter.status);
      if (this.apptFilter.from_date) params.set('from_date', this.apptFilter.from_date);
      if (this.apptFilter.to_date)   params.set('to_date',   this.apptFilter.to_date);
      const qs = params.toString();
      const res = await this.api('/admin/appointments' + (qs ? '?' + qs : ''));
      if (res && res.ok) this.appointments = await res.json();
    },
    async updateApptStatus(appt, status) {
      const label = status === 'completed' ? 'complete' : 'cancel';
      if (!confirm(`Mark this appointment as ${label}d?`)) return;
      const res = await this.api(`/admin/appointments/${appt.id}`, {
        method: 'PUT',
        body: JSON.stringify({ status }),
      });
      if (res && res.ok) {
        appt.status = status;
        this.apptMsg = `Marked as ${status}`;
        setTimeout(() => { this.apptMsg = ''; }, 2500);
      }
    },
```

- [ ] **Step 3: Run full suite + manual verify**

```bash
pytest --tb=short -q
```

Expected: 119 pass. Start dev server, verify appointments tab: filter by status, mark complete/cancel.

- [ ] **Step 4: Commit**

```bash
git add frontend/admin/index.html
git commit -m "feat: admin dashboard — appointments tab (list + filters + status update)"
```

---

### Task 6: Schedule Tab

**Files:**
- Modify: `frontend/admin/index.html` — replace `TAB:SCHEDULE` placeholder + schedule JS stubs

**Interfaces:**
- Consumes: `GET /admin/weekly-template` → `list[WeeklyTemplateOut]` (only rows that exist; may be missing days)
- `WeeklyTemplateOut` fields: `dow` (0=Mon…6=Sun), `start_time` (HH:MM:SS), `end_time` (HH:MM:SS), `slot_duration_min` (int), `is_active` (bool)
- Consumes: `PUT /admin/weekly-template/{dow}` body `{ start_time, end_time, slot_duration_min, is_active }` → `WeeklyTemplateOut`
- Consumes: `GET /admin/date-overrides` → `list[DateOverrideOut]`
- `DateOverrideOut` fields: `date` (YYYY-MM-DD), `is_blocked` (bool), `custom_start` (HH:MM:SS|null), `custom_end` (HH:MM:SS|null)
- Consumes: `POST /admin/date-overrides` body `{ date, is_blocked, custom_start, custom_end }` → `DateOverrideOut` (201, upsert)
- Consumes: `DELETE /admin/date-overrides/{date}` → 204

**Note on time format:** The API returns times as `HH:MM:SS` strings. HTML `<input type="time">` uses `HH:MM`. Slice to 5 chars when loading: `t.slice(0, 5)`.

- [ ] **Step 1: Replace Schedule HTML placeholder**

Find and replace:

```
      <!-- TAB:SCHEDULE:START -->
      <div x-show="currentTab === 'schedule'">
        <p class="text-gray-400 text-sm">Schedule — coming in Task 6</p>
      </div>
      <!-- TAB:SCHEDULE:END -->
```

Replace with:

```
      <!-- TAB:SCHEDULE:START -->
      <div x-show="currentTab === 'schedule'">
        <h2 class="text-2xl font-bold text-[#241914] mb-6">Schedule</h2>

        <!-- Weekly Template -->
        <div class="bg-white rounded-2xl shadow-sm p-6 mb-6">
          <h3 class="text-base font-semibold text-[#241914] mb-4">Weekly Template</h3>
          <div class="space-y-3">
            <template x-for="day in weeklyTemplate" :key="day.dow">
              <div class="flex items-center gap-4 py-1">
                <div class="w-20">
                  <label class="flex items-center gap-2 cursor-pointer select-none">
                    <input type="checkbox" x-model="day.is_active" @change="saveWeeklyDay(day)"
                      class="rounded border-gray-300 text-[#B86E78]" />
                    <span class="text-sm font-medium"
                      x-text="['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][day.dow]"></span>
                  </label>
                </div>
                <div x-show="day.is_active" class="flex items-center gap-3 flex-wrap">
                  <input type="time" x-model="day.start_time" @change="saveWeeklyDay(day)"
                    class="border border-gray-200 rounded-lg px-2 py-1 text-sm focus:outline-none focus:border-[#B86E78]" />
                  <span class="text-gray-400 text-sm">–</span>
                  <input type="time" x-model="day.end_time" @change="saveWeeklyDay(day)"
                    class="border border-gray-200 rounded-lg px-2 py-1 text-sm focus:outline-none focus:border-[#B86E78]" />
                  <div class="flex items-center gap-1">
                    <input type="number" x-model.number="day.slot_duration_min"
                      @change="saveWeeklyDay(day)"
                      min="15" step="15"
                      class="w-16 border border-gray-200 rounded-lg px-2 py-1 text-sm focus:outline-none focus:border-[#B86E78]" />
                    <span class="text-xs text-gray-400">min/slot</span>
                  </div>
                </div>
              </div>
            </template>
          </div>
          <p x-show="scheduleMsg" x-text="scheduleMsg"
            class="mt-3 text-sm text-green-700"></p>
        </div>

        <!-- Date Overrides -->
        <div class="bg-white rounded-2xl shadow-sm p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-semibold text-[#241914]">Date Overrides</h3>
            <button @click="showOverrideForm = !showOverrideForm"
              class="bg-[#B86E78] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#a5606a]">
              + Add Override
            </button>
          </div>

          <!-- Add override form -->
          <div x-show="showOverrideForm" class="bg-[#F4EDE5] rounded-xl p-4 mb-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Date *</label>
                <input type="date" x-model="overrideForm.date"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div class="flex items-center gap-2 pt-5">
                <input type="checkbox" x-model="overrideForm.is_blocked" id="ov_blocked"
                  class="rounded border-gray-300" />
                <label for="ov_blocked" class="text-sm font-medium select-none">Block entire day</label>
              </div>
              <div x-show="!overrideForm.is_blocked">
                <label class="block text-xs font-medium text-gray-700 mb-1">Custom Start</label>
                <input type="time" x-model="overrideForm.custom_start"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
              <div x-show="!overrideForm.is_blocked">
                <label class="block text-xs font-medium text-gray-700 mb-1">Custom End</label>
                <input type="time" x-model="overrideForm.custom_end"
                  class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#B86E78]" />
              </div>
            </div>
            <div class="mt-3 flex gap-3">
              <button @click="saveOverride()"
                class="bg-[#B86E78] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#a5606a]">
                Save Override
              </button>
              <button @click="showOverrideForm = false; overrideForm = { date: '', is_blocked: true, custom_start: '', custom_end: '' }"
                class="px-4 py-2 text-sm text-gray-500 hover:text-gray-700">Cancel</button>
            </div>
          </div>

          <!-- Override list -->
          <div class="space-y-2">
            <template x-for="ov in dateOverrides" :key="ov.date">
              <div class="flex items-center justify-between py-2 border-b border-gray-100">
                <div>
                  <span class="font-medium text-sm" x-text="ov.date"></span>
                  <span x-show="ov.is_blocked"
                    class="ml-2 text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded">Blocked</span>
                  <span x-show="!ov.is_blocked"
                    class="ml-2 text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded"
                    x-text="(ov.custom_start ? ov.custom_start.slice(0,5) : '') + ' – ' + (ov.custom_end ? ov.custom_end.slice(0,5) : '')"></span>
                </div>
                <button @click="deleteOverride(ov.date)" class="text-xs text-red-500 hover:underline">Remove</button>
              </div>
            </template>
            <p x-show="dateOverrides.length === 0" class="text-sm text-gray-400 py-2">No overrides configured</p>
          </div>
        </div>
      </div>
      <!-- TAB:SCHEDULE:END -->
```

- [ ] **Step 2: Replace schedule JS stubs**

Find and replace:

```
    async loadSchedule() { /* STUB:loadSchedule */ },
    async saveWeeklyDay(_day) { /* STUB:saveWeeklyDay */ },
    async saveOverride() { /* STUB:saveOverride */ },
    async deleteOverride(_date) { /* STUB:deleteOverride */ },
```

Replace with:

```
    async loadSchedule() {
      const [tmplRes, ovRes] = await Promise.all([
        this.api('/admin/weekly-template'),
        this.api('/admin/date-overrides'),
      ]);
      if (tmplRes && tmplRes.ok) {
        const existing = await tmplRes.json();
        // Ensure all 7 days represented; API only returns rows that exist
        this.weeklyTemplate = [0, 1, 2, 3, 4, 5, 6].map(dow => {
          const found = existing.find(d => d.dow === dow);
          if (found) return { ...found, start_time: found.start_time.slice(0, 5), end_time: found.end_time.slice(0, 5) };
          return { dow, start_time: '09:00', end_time: '18:00', slot_duration_min: 90, is_active: false };
        });
      }
      if (ovRes && ovRes.ok) this.dateOverrides = await ovRes.json();
    },
    async saveWeeklyDay(day) {
      const body = {
        start_time: day.start_time,
        end_time: day.end_time,
        slot_duration_min: day.slot_duration_min,
        is_active: day.is_active,
      };
      const res = await this.api(`/admin/weekly-template/${day.dow}`, { method: 'PUT', body: JSON.stringify(body) });
      if (res && res.ok) {
        this.scheduleMsg = '✓ Saved';
        setTimeout(() => { this.scheduleMsg = ''; }, 2000);
      }
    },
    async saveOverride() {
      if (!this.overrideForm.date) return;
      const body = {
        date: this.overrideForm.date,
        is_blocked: this.overrideForm.is_blocked,
        custom_start: this.overrideForm.is_blocked ? null : (this.overrideForm.custom_start || null),
        custom_end:   this.overrideForm.is_blocked ? null : (this.overrideForm.custom_end   || null),
      };
      const res = await this.api('/admin/date-overrides', { method: 'POST', body: JSON.stringify(body) });
      if (res && res.ok) {
        await this.loadSchedule();
        this.showOverrideForm = false;
        this.overrideForm = { date: '', is_blocked: true, custom_start: '', custom_end: '' };
      }
    },
    async deleteOverride(date) {
      if (!confirm('Remove this date override?')) return;
      const res = await this.api(`/admin/date-overrides/${date}`, { method: 'DELETE' });
      if (res && (res.ok || res.status === 204))
        this.dateOverrides = this.dateOverrides.filter(o => o.date !== date);
    },
```

- [ ] **Step 3: Run full suite + manual verify**

```bash
pytest --tb=short -q
```

Expected: 119 pass. Start dev server, verify schedule tab: toggle a day on/off, change time, add a date override (blocked + custom hours), remove it.

- [ ] **Step 4: Commit**

```bash
git add frontend/admin/index.html
git commit -m "feat: admin dashboard — schedule tab (weekly template + date overrides)"
```

---

## Self-Review

### 1. Spec coverage

| Spec requirement | Task |
|---|---|
| Plain HTML + Alpine.js, no build step | All — CDN only |
| Login + JWT in localStorage | Task 1 |
| Static serving at `/dashboard` | Task 1 |
| Studio Profile tab (all 9 fields) | Task 2 |
| Services CRUD + toggles + 5 languages | Task 3 |
| Portfolio grid + CRUD | Task 4 |
| Appointments list + status filter + date range | Task 5 |
| Appointments mark complete/cancelled | Task 5 |
| Schedule weekly template (7 days, toggle, times, slot_duration) | Task 6 |
| Schedule date overrides (block + custom hours, add/remove) | Task 6 |
| Brand colors: `#F4EDE5`, `#241914`, `#B86E78`, `#A6864F` | Task 1 (Tailwind config) |
| Auto-logout on 401/403 | Task 1 (`api()` helper) |

### 2. Placeholder scan

No TBD, TODO, or placeholder prose in the task steps. All HTML and JS is complete and functional.

### 3. Type consistency

- `AdminServiceIn`: does not include `id`, `created_at`, `updated_at` — handled in `toggleServiceField` by constructing body from only the correct fields ✓
- `AdminPortfolioIn`: same pattern — `togglePortfolioVisibility` constructs body manually ✓
- Time fields from API are `HH:MM:SS`; truncated to `HH:MM` before binding to `<input type="time">` in `loadSchedule()` ✓
- `service_id` in portfolio form: empty string `""` converted to `null` before POST/PUT ✓
