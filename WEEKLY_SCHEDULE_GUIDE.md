# 📅 Weekly Schedule & Meal Plan Guide

**CrossFit Health OS** - Weekly Training Schedule & Auto Meal Planning

---

## 🎯 Overview

O sistema agora suporta **programação semanal de treinos** com **geração automática de planos alimentares** sincronizados com os horários de treino.

### Features Implementadas

✅ **Weekly Training Schedule**
- Defina quantas sessões de treino por dia (máx 3)
- Configure horários específicos para cada sessão
- Marque dias de descanso
- Suporte para múltiplas metodologias (HWPO, Mayhem, CompTrain)

✅ **Auto Meal Planning**
- Refeições pré-treino (default: 60min antes)
- Refeições pós-treino (default: 30min depois)
- Refeições padrão (café, almoço, jantar)
- Ajuste automático para evitar conflitos

✅ **Fixes de Segurança**
- Validação robusta de JWT auth
- Error handling em queries Supabase
- Validação de ownership em todos os endpoints
- Validators Pydantic para datas e ranges

---

## 📋 API Endpoints

Base URL: `http://localhost:8000/api/v1/schedule`

### 1. Create Weekly Schedule

**POST** `/weekly`

Cria um novo cronograma semanal de treinos.

**Request Body:**
```json
{
  "name": "HWPO 5x per week",
  "methodology": "hwpo",
  "schedule": {
    "monday": {
      "day": "monday",
      "sessions": [
        {
          "time": "06:00",
          "duration_minutes": 90,
          "workout_type": "strength",
          "notes": "Heavy squats + accessory"
        }
      ],
      "rest_day": false
    },
    "tuesday": {
      "day": "tuesday",
      "sessions": [
        {
          "time": "06:00",
          "duration_minutes": 60,
          "workout_type": "metcon"
        }
      ],
      "rest_day": false
    },
    "wednesday": {
      "day": "wednesday",
      "sessions": [
        {
          "time": "18:00",
          "duration_minutes": 45,
          "workout_type": "skill",
          "notes": "Gymnastics - handstands"
        }
      ],
      "rest_day": false
    },
    "thursday": {
      "day": "thursday",
      "sessions": [
        {
          "time": "06:00",
          "duration_minutes": 75,
          "workout_type": "mixed"
        },
        {
          "time": "18:00",
          "duration_minutes": 30,
          "workout_type": "conditioning",
          "notes": "Zone 2 bike"
        }
      ],
      "rest_day": false
    },
    "friday": {
      "day": "friday",
      "sessions": [
        {
          "time": "06:00",
          "duration_minutes": 60,
          "workout_type": "metcon",
          "notes": "Competition simulation"
        }
      ],
      "rest_day": false
    },
    "saturday": {
      "day": "saturday",
      "sessions": [],
      "rest_day": true
    },
    "sunday": {
      "day": "sunday",
      "sessions": [],
      "rest_day": true
    }
  },
  "start_date": "2026-02-10",
  "end_date": null,
  "active": true
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "HWPO 5x per week",
  "methodology": "hwpo",
  "schedule": {...},
  "start_date": "2026-02-10",
  "end_date": null,
  "active": true,
  "created_at": "2026-02-08T12:00:00Z",
  "updated_at": "2026-02-08T12:00:00Z"
}
```

**Validações:**
- ✅ Máximo 3 sessões por dia
- ✅ Dias de descanso não podem ter sessões
- ✅ Duração entre 30-180 minutos
- ✅ `end_date` deve ser depois de `start_date`

---

### 2. Get Active Schedule

**GET** `/weekly/active`

Retorna o cronograma ativo do usuário.

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "name": "HWPO 5x per week",
  "schedule": {...},
  "active": true
}
```

**Errors:**
- `404 Not Found` - Nenhum cronograma ativo

---

### 3. List Schedules

**GET** `/weekly?limit=10`

Lista todos os cronogramas do usuário (ordenado por data de criação).

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "name": "HWPO 5x per week",
    "active": true,
    "start_date": "2026-02-10",
    "created_at": "2026-02-08T12:00:00Z"
  },
  ...
]
```

---

### 4. Update Schedule

**PATCH** `/weekly/{schedule_id}`

Atualiza um cronograma existente.

**Request Body:** (mesma estrutura do POST)

**Response:** `200 OK`

---

### 5. Delete Schedule

**DELETE** `/weekly/{schedule_id}`

Deleta um cronograma.

**Response:** `204 No Content`

---

### 6. Generate Meal Plan (AUTO)

**POST** `/weekly/{schedule_id}/meal-plan`

Gera automaticamente um plano alimentar baseado no cronograma de treinos.

**Query Parameters:**
- `pre_workout_offset_minutes` (default: -60) - Minutos antes do treino
- `post_workout_offset_minutes` (default: 30) - Minutos depois do treino

**Request:**
```bash
POST /weekly/abc-123/meal-plan?pre_workout_offset_minutes=-90&post_workout_offset_minutes=45
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "training_schedule_id": "abc-123",
  "meal_plans": {
    "monday": {
      "day": "monday",
      "meals": [
        {
          "meal_type": "pre_workout",
          "time": "04:30",
          "duration_minutes": 20,
          "notes": "Before 06:00 session",
          "macros": null
        },
        {
          "meal_type": "breakfast",
          "time": "07:00",
          "duration_minutes": 30,
          "macros": null
        },
        {
          "meal_type": "post_workout",
          "time": "08:15",
          "duration_minutes": 30,
          "notes": "After 06:00 session",
          "macros": null
        },
        {
          "meal_type": "lunch",
          "time": "12:00",
          "duration_minutes": 45,
          "macros": null
        },
        {
          "meal_type": "dinner",
          "time": "19:00",
          "duration_minutes": 45,
          "macros": null
        }
      ],
      "training_day": true,
      "total_calories": null
    },
    "saturday": {
      "day": "saturday",
      "meals": [
        {
          "meal_type": "breakfast",
          "time": "07:00",
          "duration_minutes": 30
        },
        {
          "meal_type": "lunch",
          "time": "12:00",
          "duration_minutes": 45
        },
        {
          "meal_type": "dinner",
          "time": "19:00",
          "duration_minutes": 45
        }
      ],
      "training_day": false,
      "total_calories": null
    }
  },
  "pre_workout_offset_minutes": -90,
  "post_workout_offset_minutes": 45,
  "created_at": "2026-02-08T12:05:00Z"
}
```

**Lógica de Geração:**

1. **Dias de treino:**
   - Pre-workout meal: N minutos antes de cada sessão
   - Post-workout meal: N minutos depois de cada sessão
   - Meals padrão: Café (07:00), Almoço (12:00), Jantar (19:00)
   - Ordenação automática por horário

2. **Dias de descanso:**
   - Apenas meals padrão (3 refeições)

3. **Múltiplas sessões:**
   - Cria pre/post para cada sessão
   - Pode resultar em 5-7 refeições no dia

---

### 7. Get Meal Plan

**GET** `/weekly/{schedule_id}/meal-plan`

Retorna o plano alimentar mais recente para o cronograma.

**Response:** `200 OK` (mesma estrutura do POST)

---

## 🗄️ Database Schema

### `weekly_schedules`

```sql
CREATE TABLE weekly_schedules (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(100),
    methodology VARCHAR(20) CHECK (methodology IN ('hwpo', 'mayhem', 'comptrain', 'custom')),
    schedule JSONB NOT NULL,  -- Estrutura do cronograma
    start_date DATE NOT NULL,
    end_date DATE,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

### `weekly_meal_plans`

```sql
CREATE TABLE weekly_meal_plans (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    training_schedule_id UUID REFERENCES weekly_schedules(id),
    meal_plans JSONB NOT NULL,  -- Meals organizadas por dia
    pre_workout_offset_minutes INT DEFAULT -60,
    post_workout_offset_minutes INT DEFAULT 30,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

### Helper Functions

```sql
-- Get current week's schedule
SELECT get_current_week_schedule('user_uuid');

-- Get today's training sessions
SELECT get_today_training_sessions('user_uuid');

-- Get today's meals
SELECT get_today_meals('user_uuid');
```

---

## 🔧 Como Usar (Frontend/Mobile)

### Fluxo Completo

```javascript
// 1. Criar cronograma de treinos
const scheduleResponse = await fetch('/api/v1/schedule/weekly', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: "HWPO 5x per week",
    methodology: "hwpo",
    schedule: {
      monday: {
        day: "monday",
        sessions: [
          { time: "06:00", duration_minutes: 90, workout_type: "strength" }
        ],
        rest_day: false
      },
      // ... outros dias
    },
    start_date: "2026-02-10"
  })
});

const schedule = await scheduleResponse.json();

// 2. Gerar plano alimentar automático
const mealPlanResponse = await fetch(
  `/api/v1/schedule/weekly/${schedule.id}/meal-plan?pre_workout_offset_minutes=-90`,
  {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  }
);

const mealPlan = await mealPlanResponse.json();

// 3. Exibir no calendário/dashboard
console.log('Refeições de segunda:', mealPlan.meal_plans.monday.meals);
```

---

## 🎨 UI Suggestions

### Tela de Configuração (Wizard)

**Step 1: Escolher Metodologia**
```
[ ] HWPO (Mat Fraser)
[ ] Mayhem (Rich Froning)
[ ] CompTrain (Ben Bergeron)
[ ] Custom
```

**Step 2: Configurar Dias da Semana**

Para cada dia:
```
Segunda-feira
  [ ] Dia de descanso
  
  Sessões de treino:
  + Adicionar sessão
  
  Sessão 1:
    Horário: [06:00] ⏰
    Duração: [90] minutos
    Tipo: [Strength ▼]
    Notas: [_____________]
```

**Step 3: Configurar Alimentação**

```
Pre-treino: [60] minutos antes ⏱️
Pós-treino: [30] minutos depois ⏱️

[ ] Gerar plano alimentar automaticamente
```

**Step 4: Revisão**

```
Resumo:
- 5 dias de treino
- 2 dias de descanso
- 7 sessões por semana
- 35-40 refeições por semana

[Criar Cronograma]
```

### Dashboard (Visualização)

```
┌─────────────────────────────────────┐
│ Hoje - Segunda-feira                │
│                                     │
│ 🏋️ 06:00 - Strength (90min)        │
│ 🍽️ 04:30 - Pre-workout             │
│ 🍽️ 08:00 - Post-workout            │
│ 🍽️ 12:00 - Lunch                   │
│ 🍽️ 19:00 - Dinner                  │
│                                     │
│ [Ver Semana Completa]               │
└─────────────────────────────────────┘
```

---

## ✅ Fixes Implementados

### 1. Auth Fix
```python
# ✅ Antes (vulnerável)
if not user:
    raise HTTPException(...)
response = supabase_client.table("users").eq("auth_user_id", user.user.id)  # ❌ Crash se user.user=None

# ✅ Depois (seguro)
if not user or not user.user:
    raise HTTPException(...)
```

### 2. Error Handling
```python
# ✅ Antes (sem verificação)
response = supabase_client.table(...).execute()
return response.data[0]  # ❌ Crash se response.error

# ✅ Depois (robusto)
response = supabase_client.table(...).execute()
data = handle_supabase_response(response, "Error message")
return data[0]
```

### 3. Validators
```python
# ✅ volume_multiplier range
volume_multiplier: float = Field(..., ge=0.0, le=2.0)

# ✅ Future dates only
@field_validator('scheduled_at')
def validate_future_date(cls, v):
    if v and v < datetime.utcnow():
        raise ValueError('Must be in future')
    return v
```

---

## 📊 Testes Recomendados

### Unit Tests
```python
def test_create_weekly_schedule():
    """Test schedule creation with multiple sessions"""
    # ...

def test_meal_plan_generation():
    """Test auto meal plan from training schedule"""
    # ...

def test_rest_day_no_sessions():
    """Ensure rest days cannot have sessions"""
    # ...

def test_multiple_sessions_per_day():
    """Test day with 2-3 training sessions"""
    # ...
```

### Integration Tests
```python
def test_schedule_to_meal_plan_flow():
    """Full flow: create schedule → generate meal plan"""
    # ...

def test_activate_deactivate_schedules():
    """Test switching between schedules"""
    # ...
```

---

## 🚀 Próximos Passos

### Melhorias Futuras

1. **Smart Meal Spacing**
   - Evitar refeições muito próximas (< 2h)
   - Ajustar horários automaticamente

2. **Macro Calculator Integration**
   - Calcular macros por refeição baseado em:
     - Tipo de refeição (pre/post workout)
     - Peso corporal
     - Objetivo (cutting, bulking, maintenance)

3. **Calendar Integration**
   - Exportar para Google Calendar
   - Notificações push para refeições/treinos

4. **Conflict Detection**
   - Alertar se treinos/refeições conflitam com eventos do calendário

5. **Template Library**
   - Cronogramas pré-definidos:
     - "Iniciante 3x/semana"
     - "HWPO Competition 6x/semana"
     - "Mayhem Athlete"

---

**Implementado por:** Rehoboam AI 🔮  
**Data:** 2026-02-08  
**Status:** ✅ Pronto para testes
