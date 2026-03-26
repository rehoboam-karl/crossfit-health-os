# CrossFit Health OS - Avaliação v2

**Data:** 2026-03-26
**Versão:** 2.0
**Analista:** karl-dev

---

## O que mudou desde a v1

### ✅ Implementado na v2

| Feature | Status | Descrição |
|---------|--------|-----------|
| Gamificação | ✅ | Badges, XP, Levels, Streaks, Leaderboard |
| Onboarding | ✅ | 5-step guided setup com XP rewards |
| Automação | ✅ | Geração semanal automática (Cron) |
| Notificações | ✅ | Streak warnings, badges, level up |

---

## Features Implementadas

### 1. Gamificação
- **10 Badge Types:**
  - 🔥 Streaks (3, 7, 30 dias)
  - 🏆 PR Breaker, Volume King
  - ⭐ Perfect Week, Monthly Warrior
  - 🌅 Early Bird, 🦉 Night Owl
- **XP System:** 200 XP por treino + bonuses por streak
- **Leveling:** Exponential XP requirements
- **Leaderboard:** Top 10 users por XP

### 2. Onboarding
- 5-step flow: Welcome → Goals → Level → Schedule → Confirm
- Auto-creates schedule after completion
- Awards 300 XP for completing

### 3. Automação
- `AutomationService.generate_weekly_program_for_user()` 
- Called on schedule or via cron (Sunday)
- Creates workout templates for the week
- Sends notification when ready

### 4. Notificações
- `NotificationService` com preferências
- Tipos: workout_reminder, streak_warning, new_badge, level_up, weekly_summary
- Preferences configuráveis por usuário

---

## Gaps Remanescentes

### 🔴 Ainda Críticos

| Issue | Descrição | Prioridade |
|-------|-----------|------------|
| **Database migrations** | Tabelas gamificação não existem no Supabase | ALTA |
| **Frontend JS (CHOS)** | Método `api.post` não existe na lib frontend | ALTA |
| **Onboarding redirect** | Não redireciona automaticamente após login | MÉDIA |
| **Dashboard antigo** | Ainda usa dashboard.html, não dashboard_new.html | MÉDIA |

### 🟡 Importantes

| Issue | Descrição |
|-------|-----------|
| **Cron job real** | Automação precisa de cron real (n8n/supabase) |
| **Email notifications** | Sistema existe mas não envia emails |
| **Mobile responsive** | Bootstrap desktop-first ainda |

### 🟢 Desejáveis

| Feature |
|---------|
| Social sharing |
| Video demos |
| Apple Watch integration |

---

## Fluxo de Uso Atualizado

### Novo fluxo (pós-v2):
```
Novo usuário → Registro → Onboarding (5 steps) → Dashboard
                                              ↓
                              XP +300, Schedule criado
                                              ↓
                 Sunday: Sistema gera programa automaticamente
                                              ↓
         Usuário recebe notificação → Faz treino → XP +200+
                                              ↓
                            Badge awarded? → Notificação

Dias seguintes:
  → Lembrete de treino (se configurado)
  → Streak warning (se falhou 1 dia)
  → Motivation notification (a cada 3 dias)
```

### Melhor que antes ✅
- Não precisa clicar "Generate" toda semana
- Motivação via badges e streaks
- Progresso visual (XP bar, levels)

---

## Próximos Passos

### 1. Fix Database Schema
```sql
-- Tabelas necessárias:
CREATE TABLE user_stats (
    user_id UUID PRIMARY KEY,
    xp INT DEFAULT 0,
    level INT DEFAULT 1,
    current_streak INT DEFAULT 0,
    longest_streak INT DEFAULT 0
);

CREATE TABLE user_badges (
    id UUID PRIMARY KEY,
    user_id UUID,
    badge_id VARCHAR,
    earned_at TIMESTAMP
);

CREATE TABLE notifications (
    id UUID PRIMARY KEY,
    user_id UUID,
    type VARCHAR,
    title TEXT,
    body TEXT,
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP
);
```

### 2. Fix Frontend CHOS library
- Adicionar `api.post()`, `api.patch()` methods
- Testar com backend real

### 3. Replace dashboard.html
- Substituir por dashboard_new.html com gamificação

### 4. Deploy Cron Job
- Configurar n8n ou Supabase Edge Functions
- Rodar `run_weekly_generation()` todo domingo

---

## Score

**Antes:** 7/10
**Agora:** 8.5/10

**Melhorias:**
- UX melhorou com onboarding
- Gamificação adiciona retenção
- Automação resolve problema principal

**Ainda falta:**
- Database schema real
- Teste end-to-end
- Mobile optimization
