# 🐍 Frontend Python (FastAPI + Jinja2 + jQuery)

**CrossFit Health OS** - Frontend 100% Python, sem Node.js

---

## 🎯 Por Que Python?

**Antes:** Next.js 14 (React + TypeScript + Node.js)  
**Agora:** FastAPI + Jinja2 + jQuery + Bootstrap

**Motivo:** Manutenção mais simples para desenvolvedores Python. Sem dependência de Node.js, npm, build steps.

---

## 📁 Estrutura

```
backend/
├── app/
│   ├── templates/              # Jinja2 HTML Templates
│   │   ├── base.html          # Layout base (Bootstrap, jQuery, Font Awesome)
│   │   ├── index.html         # Landing page
│   │   ├── login.html         # Login
│   │   ├── register.html      # Registro
│   │   ├── forgot_password.html
│   │   └── dashboard.html     # Dashboard
│   │
│   ├── static/                 # CSS + JavaScript
│   │   ├── css/
│   │   │   └── main.css       # Custom styles
│   │   └── js/
│   │       ├── main.js        # Core utilities
│   │       ├── auth.js        # Authentication
│   │       └── dashboard.js   # Dashboard logic
│   │
│   ├── web/
│   │   └── routes.py          # Web routes (serve HTML)
│   │
│   └── api/                    # API endpoints (JSON)
│       └── v1/
│           ├── auth.py
│           ├── training.py
│           └── ...
```

---

## 🚀 Como Rodar

### Desenvolvimento

```bash
cd /home/rehoboam/crossfit-health-os/backend

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Rodar servidor
uvicorn app.main:app --reload

# Abrir navegador
open http://localhost:8000
```

### Produção (Docker)

```bash
cd /home/rehoboam/crossfit-health-os
docker compose up -d
```

**Porta única:** 8000 (API + Frontend)

---

## 📄 Páginas Criadas

### 1. Landing Page (`/`)

**Arquivo:** `templates/index.html`

**Seções:**
- Hero com CTA
- 6 features principais (AI programming, adaptive training, reviews, etc)
- "How it works" (5 passos do feedback loop)
- Pricing ($29/mês)
- Footer

**Bootstrap components:**
- Navbar
- Cards
- Buttons
- Timeline

---

### 2. Login (`/login`)

**Arquivo:** `templates/login.html`

**Features:**
- Email + senha
- "Remember me" checkbox
- Link para "forgot password"
- AJAX submission via jQuery
- Error alerts
- Loading state no botão

**JavaScript:**
```javascript
$('#login-form').on('submit', function(e) {
    e.preventDefault();
    
    $.ajax({
        url: '/api/v1/auth/login',
        type: 'POST',
        data: JSON.stringify({ email, password }),
        success: function(response) {
            localStorage.setItem('access_token', response.access_token);
            localStorage.setItem('user', JSON.stringify(response.user));
            window.location.href = '/dashboard';
        },
        error: function(xhr) {
            showAlert(xhr.responseJSON.detail, 'danger');
        }
    });
});
```

---

### 3. Registro (`/register`)

**Arquivo:** `templates/register.html`

**Campos:**
- **Obrigatórios:** Nome, email, senha, confirmar senha
- **Opcionais:** Data nascimento, peso, altura, nível fitness, objetivos

**Validações client-side:**
- Password strength indicator (weak/medium/strong)
- Password match checker
- Goals checkboxes (múltipla escolha)

**Features:**
- Responsive grid (Bootstrap)
- Real-time password validation
- Color-coded feedback

---

### 4. Forgot Password (`/forgot-password`)

**Arquivo:** `templates/forgot_password.html`

**Flow:**
1. Usuário entra email
2. AJAX call para `/api/v1/auth/forgot-password`
3. Sempre mostra sucesso (segurança)
4. Email é enviado pelo backend (Supabase Auth)

**UI:**
- Form view → Success view (transition com jQuery)
- Ícone de envelope
- Botão "Back to Login"

---

### 5. Dashboard (`/dashboard`)

**Arquivo:** `templates/dashboard.html`

**Layout:**
- **Navbar:** Logo, links (Workouts, Schedule, Reviews, Profile), dropdown user
- **Welcome banner:** Gradient azul com nome do usuário
- **4 stats cards:** Readiness, sessions, week, next review
- **Today's workout:** Placeholder (criar schedule primeiro)
- **3 quick actions:** Create schedule, view workouts, profile settings
- **Getting started:** 4 passos de onboarding

**Protected:**
- Cliente checa localStorage.access_token
- Se não existe → redirect `/login`
- Navbar com logout button

---

## 🎨 Design System

### Bootstrap 5.3 (CDN)

```html
<!-- Em base.html -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
```

**Componentes usados:**
- Grid system (responsive)
- Cards
- Buttons (primary, outline, lg)
- Forms (form-control, form-label, form-check)
- Navbar
- Alerts (dismissible)
- Dropdowns
- Badges

### Custom CSS (`static/css/main.css`)

**Customizações:**
- Variáveis CSS (--primary, --primary-dark)
- Gradientes (hero, welcome banner)
- Hover effects (hover-lift)
- Timeline styling
- Animations (slideDown para alerts)
- Responsive breakpoints

**Utility classes:**
```css
.hover-lift:hover {
    transform: translateY(-5px);
    box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
}

.bg-gradient-primary {
    background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
}
```

### Icons (Font Awesome CDN)

```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
```

**Ícones usados:**
- `fa-dumbbell` (logo)
- `fa-brain` (AI)
- `fa-chart-line` (analytics)
- `fa-heartbeat` (recovery)
- `fa-utensils` (nutrition)
- etc.

---

## 🔌 JavaScript (jQuery 3.7)

### Core (`static/js/main.js`)

**Features:**
- AJAX defaults (add token header, handle 401)
- Utility functions (showAlert, formatDate, isAuthenticated)
- Smooth scroll para anchor links
- Global error handler

**AJAX Setup:**
```javascript
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        const token = localStorage.getItem('access_token');
        if (token && !settings.url.includes('/auth/')) {
            xhr.setRequestHeader('Authorization', 'Bearer ' + token);
        }
    },
    error: function(xhr) {
        if (xhr.status === 401) {
            // Token expired → redirect login
            localStorage.removeItem('access_token');
            window.location.href = '/login';
        }
    }
});
```

### Auth (`static/js/auth.js`)

**Features:**
- Password strength checker (weak/medium/strong)
- Password match indicator (registro)
- Real-time validation feedback
- Redirect se já autenticado

**Password Strength:**
```javascript
function checkPasswordStrength(password) {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[!@#$%^&*]/.test(password)) strength++;
    
    if (strength < 3) return { level: 'weak', color: 'danger' };
    if (strength < 4) return { level: 'medium', color: 'warning' };
    return { level: 'strong', color: 'success' };
}
```

### Dashboard (`static/js/dashboard.js`)

**Features:**
- Check auth on load
- Load user profile (API call)
- Get today's workout (API call)
- Logout handler

**API Wrapper:**
```javascript
const DashboardAPI = {
    getProfile: function() {
        return $.ajax({ url: '/api/v1/users/me', type: 'GET' });
    },
    getTodayWorkout: function() {
        return $.ajax({ url: '/api/v1/training/workouts/today', type: 'GET' });
    }
};
```

---

## 🔄 Fluxo de Autenticação

### 1. Login

```
User → Preenche form → Submit
       ↓
jQuery AJAX → POST /api/v1/auth/login { email, password }
       ↓
Backend → Valida → Retorna JWT + user data
       ↓
Frontend → localStorage.setItem('access_token', token)
        → localStorage.setItem('user', JSON.stringify(user))
        → window.location.href = '/dashboard'
```

### 2. Dashboard (Protected Page)

```
User → Acessa /dashboard
       ↓
JavaScript → Checa localStorage.access_token
       ↓
Se não existe → Redirect /login
Se existe → Carrega página
       ↓
AJAX call → GET /api/v1/users/me (com token no header)
       ↓
Se 200 → Exibe dados
Se 401 → Remove token → Redirect /login
```

### 3. API Calls

```
Toda requisição AJAX passa por interceptor:

beforeSend: function(xhr) {
    const token = localStorage.getItem('access_token');
    xhr.setRequestHeader('Authorization', 'Bearer ' + token);
}

Se response 401 → Interceptor global remove token → redirect
```

---

## 📊 Comparação

| Feature | Next.js | FastAPI + Jinja2 |
|---------|---------|------------------|
| **Build step** | ✅ npm run build | ❌ Não precisa |
| **Hot reload** | ✅ Next dev server | ✅ uvicorn --reload |
| **Linguagem** | TypeScript + Python | Python only |
| **Complexidade** | Alta (React, hooks, state) | Baixa (HTML + jQuery) |
| **SEO** | ✅ SSR/SSG | ✅ Server-side render |
| **Type safety** | ✅ TypeScript | ❌ JavaScript |
| **Manutenção** | Requer Node.js conhecimento | ✅ Python devs OK |
| **Deploy** | 2 containers (backend + frontend) | 1 container |
| **Performance** | ⚡ Fast (bundle optimization) | ⚡ Fast (CDN assets) |

---

## ✅ Vantagens

1. **Stack único:** Python para tudo
2. **Sem build:** Edit HTML → F5 reload
3. **Debugging simples:** View source = código real
4. **CDN assets:** Bootstrap/jQuery carregam rápido
5. **Deploy simples:** Um container, uma porta
6. **Manutenção:** Qualquer dev Python consegue editar
7. **Git diff:** HTML legível (não JS compilado)

---

## ⚠️ Trade-offs

1. **Sem components:** HTML duplicado (vs React reusável)
2. **jQuery:** Mais verboso que React hooks
3. **No TypeScript:** Menos type safety
4. **Manual DOM:** Mais código para UI updates
5. **SEO limitado:** Sem pre-rendering de páginas dinâmicas

---

## 🛠️ Como Adicionar Páginas

### 1. Criar template

```bash
touch backend/app/templates/nova_pagina.html
```

```html
{% extends "base.html" %}

{% block title %}Nova Página{% endblock %}

{% block content %}
<div class="container py-5">
    <h1>Minha Nova Página</h1>
    <p>Conteúdo aqui</p>
</div>
{% endblock %}

{% block extra_js %}
<script>
    $(document).ready(function() {
        // JavaScript específico desta página
    });
</script>
{% endblock %}
```

### 2. Adicionar rota

```python
# backend/app/web/routes.py
@router.get("/nova-pagina")
async def nova_pagina(request: Request):
    return templates.TemplateResponse("nova_pagina.html", {"request": request})
```

### 3. Acessar

```
http://localhost:8000/nova-pagina
```

---

## 📚 Referências

**Bootstrap 5.3:**
- Docs: https://getbootstrap.com/docs/5.3/
- Grid: https://getbootstrap.com/docs/5.3/layout/grid/
- Components: https://getbootstrap.com/docs/5.3/components/

**jQuery 3.7:**
- Docs: https://api.jquery.com/
- AJAX: https://api.jquery.com/jQuery.ajax/
- Events: https://api.jquery.com/category/events/

**Jinja2:**
- Docs: https://jinja.palletsprojects.com/
- Templates: https://jinja.palletsprojects.com/en/3.1.x/templates/

**Font Awesome:**
- Icons: https://fontawesome.com/icons
- CDN: https://cdnjs.com/libraries/font-awesome

---

## 🚀 Próximos Passos

### TODO (Dashboard Subpages)

1. **Workouts (`/dashboard/workouts`):**
   - Lista de sessões recentes
   - Filtros por tipo, data
   - Modal para ver detalhes
   - Form para log de feedback

2. **Schedule (`/dashboard/schedule`):**
   - Calendar view (FullCalendar.js?)
   - Form para criar weekly schedule
   - Button "Generate AI Program"
   - Visualização de meal plan

3. **Reviews (`/dashboard/reviews`):**
   - Lista de weekly reviews
   - Cards com strengths/weaknesses
   - Chart de progressão
   - Button "Generate Review"

4. **Profile (`/dashboard/profile`):**
   - Form para editar peso, altura, goals
   - Upload de avatar
   - Conexões (HealthKit, Calendar)
   - Settings (notificações, etc)

---

## 💡 Dicas de Manutenção

### Debug HTML

```python
# Adicionar print no template
{{ variable|pprint }}

# Passar variáveis do backend
return templates.TemplateResponse("page.html", {
    "request": request,
    "user": user_data,
    "debug": True
})
```

### Debug AJAX

```javascript
// No navegador (F12 → Console)
$('#meu-form').on('submit', function(e) {
    e.preventDefault();
    console.log('Form data:', $(this).serialize());
});

// Ver todas requests AJAX
$(document).ajaxSend(function(event, jqxhr, settings) {
    console.log('AJAX:', settings.type, settings.url);
});
```

### Live Reload

```bash
# Backend
uvicorn app.main:app --reload

# Templates editados → F5 no navegador
# CSS/JS editados → Ctrl+Shift+R (hard reload)
```

---

**Stack:** Python 3.12 + FastAPI + Jinja2 + jQuery 3.7 + Bootstrap 5.3  
**Port:** 8000 (API + Frontend em uma porta)  
**Deploy:** Docker único container  
**Manutenção:** ✅ Python devs friendly
