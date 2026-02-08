# 🎨 CrossFit Health OS - Frontend Python Completo

## ✅ O QUE FOI CRIADO

### Frontend Moderno em Python (FastAPI + Jinja2)

Substituímos o Next.js por um **frontend totalmente em Python** usando:
- **FastAPI** - Serve páginas HTML renderizadas server-side
- **Jinja2** - Templates dinâmicos
- **Tailwind CSS** - Utility-first CSS framework
- **Bootstrap 5** - Componentes UI prontos
- **ApexCharts** - Gráficos interativos profissionais
- **Alpine.js** - Reatividade JavaScript leve
- **Font Awesome 6** - Ícones modernos

---

## 📁 ESTRUTURA CRIADA

```
backend/
├── app/
│   ├── templates/                 # Templates Jinja2
│   │   ├── base.html             # Layout base (sidebar, header)
│   │   ├── dashboard.html        # Dashboard principal
│   │   ├── training.html         # Treinos e PRs
│   │   ├── health.html           # Biomarkers e recovery
│   │   └── nutrition.html        # Macros e refeições
│   ├── static/                    # Arquivos estáticos
│   │   ├── css/
│   │   ├── js/
│   │   └── img/
│   └── web/                       # Routers web
│       ├── __init__.py
│       └── routes.py             # Rotas HTML + mock data
```

---

## 🎨 PÁGINAS CRIADAS

### 1. **Dashboard** (`/dashboard`)

**Features:**
- ✅ 4 cards de estatísticas:
  - Readiness Score (gauge animado)
  - Total de Workouts
  - HRV Status
  - Calorias do dia
  
- ✅ Workout de hoje (card grande):
  - Metodologia (HWPO/Mayhem/CompTrain)
  - Movimentos ajustados
  - Multiplicador de volume
  - Recomendação adaptativa
  - Botão "Iniciar Treino"
  
- ✅ Status de Recuperação:
  - Gauge radial (readiness)
  - Barras de: Sono, Estresse, Dor Muscular
  - Botão "Atualizar Métricas"
  
- ✅ Gráficos ApexCharts:
  - Volume de Treino (30 dias) - Area Chart
  - HRV & Readiness (30 dias) - Line Chart dual-axis

### 2. **Training** (`/training`)

**Features:**
- ✅ Botões de ação:
  - "Gerar Treino Adaptativo" (conecta à API)
  - "Iniciar Treino Manual"
  
- ✅ Feed de treinos recentes (cards):
  - Data, nome, tipo (metcon/strength/hero)
  - Score, RPE (estrelas)
  - Notes do atleta
  - Botões: Ver Detalhes, Repetir
  
- ✅ Personal Records (cards dourados):
  - Troféu icon
  - Movimento + valor
  - Data do PR
  
- ✅ Gráficos:
  - Distribuição por tipo (Donut Chart)
  - RPE Médio 7 dias (Bar Chart)

### 3. **Health** (`/health`)

**Features:**
- ✅ Upload de Exames (banner chamativo):
  - "Upload de Exames Laboratoriais"
  - OCR Inteligente (GPT-4 Vision)
  
- ✅ Grid de Biomarcadores (4 cards):
  - Status: Optimal/Normal/High/Low
  - Valor + unidade
  - Data do exame
  - Cores por status
  
- ✅ Tabela de Recovery (7 dias):
  - Readiness Score (círculo colorido)
  - HRV, Sono
  - Status: Excelente/Normal/Fadiga
  
- ✅ Gráfico de tendência (6 meses):
  - Testosterone, Vitamin D, Cortisol
  - Line Chart multi-série

### 4. **Nutrition** (`/nutrition`)

**Features:**
- ✅ Macro Rings (3 gauges radiais):
  - Proteína (azul)
  - Carboidratos (verde)
  - Gordura (laranja)
  - Progresso vs meta
  
- ✅ Card de Calorias Totais:
  - Consumidas vs Meta
  - Percentual da meta
  
- ✅ Formulário "Adicionar Refeição":
  - Dropdown de tipo
  - Inputs: Calorias, P/C/F
  - Botão "Foto da Refeição (IA)"
  
- ✅ Feed de Refeições do dia:
  - Horário, nome
  - Macros detalhados
  - Botões: Editar, Deletar
  
- ✅ Gráfico Semanal:
  - Tendência de P/C/F (7 dias)
  - Line Chart multi-série

---

## 🎯 LAYOUT & DESIGN

### Sidebar (Escura)
- Gradiente preto → azul escuro
- Logo + nome
- Navegação:
  - Dashboard
  - Treinamento
  - Saúde & Recovery
  - Nutrição
  - Personal Records
  - Integrações
  - Configurações
- Perfil do usuário (fixo no bottom)

### Header (Branco)
- Título da página + subtítulo
- Data atual (atualizada em JS)
- Notificações (badge vermelho)

### Cards
- Sombra suave
- Hover effect: translateY + shadow
- Arredondamento moderno (rounded-xl)
- Ícones coloridos em círculos

### Cores
- Primary: Indigo (#6366f1)
- Success: Green (#10b981)
- Warning: Yellow (#f59e0b)
- Danger: Red (#ef4444)
- Gradientes nos cards especiais

---

## 🚀 COMO TESTAR

### 1. Instalar Dependências

```bash
cd /home/rehoboam/crossfit-health-os/backend
pip install -r requirements.txt
```

### 2. Iniciar o Servidor

```bash
# Via Uvicorn diretamente
cd /home/rehoboam/crossfit-health-os/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

ou

```bash
# Via Docker Compose (recomendado)
cd /home/rehoboam/crossfit-health-os
docker-compose up -d backend
```

### 3. Acessar o Frontend

Abra o navegador:
- **Dashboard:** http://localhost:8000/dashboard
- **Training:** http://localhost:8000/training
- **Health:** http://localhost:8000/health
- **Nutrition:** http://localhost:8000/nutrition
- **API Docs:** http://localhost:8000/docs

---

## 📊 DADOS MOCKADOS

Atualmente usando **dados mockados** (fake data) em `app/web/routes.py`:

### Funções Mock:
- `get_dashboard_data()` - Stats, workout do dia, charts
- `get_training_data()` - Workouts recentes, PRs
- `get_health_data()` - Biomarkers, recovery trend
- `get_nutrition_data()` - Macros, refeições

### Próximo Passo: Conectar ao Supabase

Substituir funções mock por queries reais:
```python
# Antes (mock)
def get_dashboard_data():
    return {"readiness_score": 85, ...}

# Depois (real)
async def get_dashboard_data(user_id: UUID):
    recovery = supabase_client.table("recovery_metrics").select("*").eq(
        "user_id", str(user_id)
    ).order("date", desc=True).limit(1).execute()
    
    return {
        "readiness_score": recovery.data[0]["readiness_score"],
        ...
    }
```

---

## 🔌 INTEGRAÇÃO COM API

### Exemplo: Gerar Workout Adaptativo

No template (`dashboard.html`):
```html
<button onclick="generateWorkout()">Gerar Treino</button>

<script>
async function generateWorkout() {
    const response = await fetch('/api/v1/training/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            user_id: "...",
            date: "2026-02-08",
            force_rest: false
        })
    });
    
    const workout = await response.json();
    // Atualizar UI com workout.adjusted_movements
}
</script>
```

---

## 🎨 CUSTOMIZAÇÃO

### Alterar Cores (Tailwind)

Edite `base.html`, seção `<script src="https://cdn.tailwindcss.com"></script>`:

```html
<script>
    tailwind.config = {
        theme: {
            extend: {
                colors: {
                    primary: '#your-color'
                }
            }
        }
    }
</script>
```

### Adicionar CSS Customizado

Crie `backend/app/static/css/custom.css`:
```css
.custom-class {
    /* seu CSS */
}
```

Inclua no `base.html`:
```html
<link rel="stylesheet" href="/static/css/custom.css">
```

---

## 📱 RESPONSIVIDADE

Todos os templates são **mobile-first** usando Tailwind:
- Grid responsivo: `grid-cols-1 md:grid-cols-2 lg:grid-cols-4`
- Sidebar colapsável (esconde em mobile)
- Cards empilham verticalmente em telas pequenas
- Gráficos se ajustam automaticamente

---

## 🔐 AUTENTICAÇÃO

### TODO: Implementar Auth

Atualmente sem autenticação. Para adicionar:

1. **Criar middleware de auth:**
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user_web(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Validar token
    # Retornar user
    pass
```

2. **Proteger rotas:**
```python
@router.get("/dashboard")
async def dashboard(request: Request, user = Depends(get_current_user_web)):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        **get_dashboard_data(user["id"])
    })
```

3. **Criar página de login:**
```html
<!-- templates/login.html -->
<form action="/login" method="POST">
    <input name="email">
    <input name="password" type="password">
    <button>Entrar</button>
</form>
```

---

## 🚢 DEPLOY NO COOLIFY

O frontend Python está **integrado no mesmo container** do backend!

Não precisa deploy separado. Quando subir o backend FastAPI no Coolify:

```yaml
# docker-compose.yml (já configurado)
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    # Frontend incluído!
```

**Acesso:**
- Frontend (HTML): `https://seu-dominio.com/dashboard`
- API REST: `https://seu-dominio.com/api/v1/...`
- API Docs: `https://seu-dominio.com/docs`

Tudo em **uma única aplicação FastAPI**! 🎉

---

## 📈 ROADMAP FRONTEND

### Fase 1: Conectar Dados Reais ✅ (Pronto para fazer)
- [ ] Substituir mock data por queries Supabase
- [ ] Implementar autenticação JWT
- [ ] Proteger rotas com middleware

### Fase 2: Funcionalidades Interativas
- [ ] Formulário de upload de exames (OCR)
- [ ] Log de refeições com foto (AI estimation)
- [ ] Iniciar/completar workout via UI
- [ ] Editar recovery metrics
- [ ] Criar/atualizar PRs

### Fase 3: Real-Time
- [ ] WebSocket para updates ao vivo
- [ ] Notificações push (Supabase Realtime)
- [ ] Sincronização HealthKit

### Fase 4: Mobile
- [ ] PWA manifest + service worker
- [ ] Install prompt
- [ ] Offline mode
- [ ] Push notifications

---

## 🎯 DIFERENÇAS vs Next.js

| Aspecto | Next.js (Antes) | FastAPI + Jinja2 (Agora) |
|---------|----------------|--------------------------|
| **Linguagem** | TypeScript/React | Python |
| **Rendering** | CSR/SSR/SSG | SSR (Server-Side Rendering) |
| **Complexidade** | Alta (build, bundle, hydration) | Baixa (templates diretos) |
| **Deploy** | 2 containers (backend + frontend) | 1 container (tudo junto) |
| **Manutenção** | 2 stacks (Python + JS) | 1 stack (só Python) |
| **Velocidade** | Initial load lento, depois rápido | Loads rápidos sempre |
| **SEO** | Excelente (SSR) | Excelente (SSR) |
| **Real-time** | React state + hooks | HTMX ou Alpine.js |

**Vantagem principal:** Stack unificado Python = menos complexidade, menos dependências, deploy mais simples!

---

## 📚 RECURSOS

### Tailwind CSS
- Docs: https://tailwindcss.com/docs
- Cheat Sheet: https://nerdcave.com/tailwind-cheat-sheet

### Bootstrap 5
- Docs: https://getbootstrap.com/docs/5.3
- Components: https://getbootstrap.com/docs/5.3/components

### ApexCharts
- Docs: https://apexcharts.com/docs
- Demos: https://apexcharts.com/javascript-chart-demos

### Jinja2
- Docs: https://jinja.palletsprojects.com
- Templates: https://jinja.palletsprojects.com/en/3.1.x/templates

---

## ✅ STATUS

**Frontend:** ✅ 100% COMPLETO (UI)  
**Integração:** ⏳ TODO (conectar dados reais)  
**Autenticação:** ⏳ TODO  
**Deploy:** ✅ Pronto (mesma stack do backend)

---

**Próximo passo:** Testar localmente e depois conectar ao Supabase real! 🚀

**Comandos:**
```bash
cd /home/rehoboam/crossfit-health-os
docker-compose up -d backend
open http://localhost:8000/dashboard
```
