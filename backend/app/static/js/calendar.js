// Calendar UI for the training scheduling page.
// Expects CHOS.api / CHOS.toast / CHOS.loading to be available from chos.js.

const ScheduleUI = (function () {
    const METHODOLOGY_PLANS = {
        hwpo: [
            { type: "accumulation", weeks: 3 },
            { type: "deload", weeks: 1 },
            { type: "intensification", weeks: 3 },
            { type: "deload", weeks: 1 },
            { type: "realization", weeks: 2 },
            { type: "test", weeks: 1 },
            { type: "transition", weeks: 1 },
        ],
        mayhem: [
            { type: "accumulation", weeks: 9 },
            { type: "intensification", weeks: 10 },
            { type: "realization", weeks: 8 },
            { type: "intensification", weeks: 8 },
            { type: "realization", weeks: 8 },
        ],
        comptrain: [
            { type: "accumulation", weeks: 4 },
            { type: "deload", weeks: 1 },
            { type: "intensification", weeks: 4 },
            { type: "deload", weeks: 1 },
            { type: "realization", weeks: 2 },
        ],
        custom: [],
    };

    const WORKOUT_COLORS = {
        strength: "primary",
        metcon: "danger",
        skill: "success",
        conditioning: "info",
        mixed: "warning",
    };

    const SHIFT_LABELS = {
        morning: "Manhã",
        afternoon: "Tarde",
        evening: "Noite",
        custom: "Custom",
    };

    let state = {
        macrocycle: null,   // active macrocycle (with microcycles)
        currentMicro: null, // microcycle being displayed
        viewDate: null,     // a date inside the currently-displayed week
        drawerSessions: [], // sessions in the open drawer
        drawerDate: null,
        templateCache: {},  // template_id -> workout template data
    };

    // ----- Date helpers (local time — never UTC) -----------------------------
    function parseISODate(s) {
        const [y, m, d] = s.split("-").map(Number);
        return new Date(y, m - 1, d);
    }

    function toISODate(d) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return `${y}-${m}-${day}`;
    }

    function addDays(d, n) {
        const x = new Date(d);
        x.setDate(x.getDate() + n);
        return x;
    }

    function mondayOf(d) {
        const wd = d.getDay(); // 0=Sun,1=Mon,...6=Sat
        const offset = wd === 0 ? -6 : 1 - wd;
        return addDays(d, offset);
    }

    function formatShortPt(d) {
        return d.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "2-digit" });
    }

    function formatLongPt(d) {
        return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "long" });
    }

    function isSameDay(a, b) {
        return a.getFullYear() === b.getFullYear()
            && a.getMonth() === b.getMonth()
            && a.getDate() === b.getDate();
    }

    // ----- Init ---------------------------------------------------------------
    function init() {
        refreshBlockPlanPreview();
        document.getElementById("macro-input-start").value = toISODate(mondayOf(new Date()));
        loadActiveMacro();
    }

    function loadActiveMacro() {
        CHOS.api.get("/api/v1/schedule/macrocycles/active")
            .done(function (data) {
                state.macrocycle = data;
                renderBanner();
                // Default view: microcycle that contains today, else the first one
                const today = new Date();
                let target = data.microcycles.find(function (m) {
                    const s = parseISODate(m.start_date), e = parseISODate(m.end_date);
                    return today >= s && today <= e;
                });
                if (!target && data.microcycles.length) target = data.microcycles[0];
                if (target) {
                    state.currentMicro = target;
                    state.viewDate = parseISODate(target.start_date);
                    showCalendar();
                    renderWeek();
                }
            })
            .fail(function (xhr) {
                if (xhr.status === 404) showEmpty();
                else console.error("Failed to load macrocycle", xhr);
            });
    }

    function showEmpty() {
        document.getElementById("empty-state").classList.remove("d-none");
        document.getElementById("macro-banner").classList.add("d-none");
        document.getElementById("calendar-container").classList.add("d-none");
    }

    function showCalendar() {
        document.getElementById("empty-state").classList.add("d-none");
        document.getElementById("macro-banner").classList.remove("d-none");
        document.getElementById("calendar-container").classList.remove("d-none");
    }

    // ----- Banner + calendar rendering --------------------------------------
    function renderBanner() {
        const m = state.macrocycle;
        document.getElementById("macro-name").textContent = m.name;
        document.getElementById("macro-dates").textContent =
            `${formatLongPt(parseISODate(m.start_date))} – ${formatLongPt(parseISODate(m.end_date))}`;
        document.getElementById("macro-methodology").textContent = m.methodology.toUpperCase();

        const micro = state.currentMicro;
        if (micro) {
            document.getElementById("macro-block-badge").textContent =
                `Bloco: ${micro.block_type || "—"}`;
            document.getElementById("macro-week-label").textContent =
                `Semana ${micro.week_index_in_block || "?"}/${totalWeeksInBlock(m, micro)} · Semana ${micro.week_index_in_macro} do macro`;
        }
    }

    function totalWeeksInBlock(macro, micro) {
        if (!macro || !micro || !micro.block_type) return "?";
        let idx = micro.week_index_in_macro, cum = 0;
        for (const b of macro.block_plan) {
            cum += b.weeks;
            if (idx <= cum) return b.weeks;
        }
        return "?";
    }

    function renderWeek() {
        const micro = state.currentMicro;
        if (!micro) return;
        const start = parseISODate(micro.start_date);
        const end = parseISODate(micro.end_date);

        document.getElementById("week-label").textContent =
            `${formatLongPt(start)} – ${formatLongPt(end)}`;

        // Reload microcycle with sessions to get fresh state
        CHOS.api.get(`/api/v1/schedule/microcycles/${micro.id}`)
            .done(function (fresh) {
                state.currentMicro = fresh;
                renderBanner();
                paintGrid(fresh);
            });
    }

    function paintGrid(micro) {
        const start = parseISODate(micro.start_date);
        const today = new Date();
        const sessionsByDate = {};
        (micro.sessions || []).forEach(function (s) {
            (sessionsByDate[s.date] = sessionsByDate[s.date] || []).push(s);
        });

        let html = "";
        for (let i = 0; i < 7; i++) {
            const d = addDays(start, i);
            const iso = toISODate(d);
            const sessions = sessionsByDate[iso] || [];
            sessions.sort(function (a, b) { return a.order_in_day - b.order_in_day; });
            const isToday = isSameDay(d, today);

            const sessionHtml = sessions.length
                ? sessions.map(function (s) {
                    const color = WORKOUT_COLORS[s.workout_type] || "secondary";
                    const shift = SHIFT_LABELS[s.shift] || (s.start_time ? s.start_time.slice(0, 5) : "");
                    const stateBadge = s.status === "generated"
                        ? '<span class="chos-badge chos-badge-success ms-1" title="Treino gerado"><i class="fas fa-check"></i></span>'
                        : s.status === "skipped"
                        ? '<span class="chos-badge chos-badge-danger ms-1" title="Dia de descanso"><i class="fas fa-bed"></i></span>'
                        : "";
                    return `
                        <div class="mb-1 p-2 rounded border border-${color} bg-light small">
                            <div class="fw-bold text-${color}">${(s.workout_type || "?").toUpperCase()} ${stateBadge}</div>
                            <div class="text-muted"><i class="fas fa-clock me-1"></i>${shift} · ${s.duration_minutes || "?"}min</div>
                            ${s.focus ? `<div class="fst-italic small">${s.focus}</div>` : ""}
                        </div>`;
                }).join("")
                : '<div class="text-muted small fst-italic">Descanso</div>\
                   <button class="btn btn-sm btn-outline-secondary w-100 mt-1" onclick="ScheduleUI.toggleRestDay(\'${iso}\')" title="Marcar como descanso oficial"><i class="fas fa-bed me-1"></i>Descanso</button>';

            html += `
                <div class="col-md">
                    <div class="chos-card h-100 ${isToday ? "border border-warning border-2" : ""}" onclick="ScheduleUI.openDayDrawer('${iso}')" style="cursor:pointer">
                        <div class="card-body p-2">
                            <div class="fw-bold ${isToday ? "text-warning" : ""} mb-2">${formatShortPt(d)}${isToday ? " · hoje" : ""}</div>
                            ${sessionHtml}
                        </div>
                    </div>
                </div>`;
        }
        document.getElementById("calendar-grid").innerHTML = html;

        // Enable "copy previous" only if there is a previous microcycle
        const prevMicro = findAdjacentMicro(micro, -1);
        document.getElementById("btn-copy-prev").disabled = !prevMicro;
    }

    function findAdjacentMicro(current, delta) {
        if (!state.macrocycle) return null;
        const list = state.macrocycle.microcycles;
        const targetIdx = current.week_index_in_macro + delta;
        return list.find(function (m) { return m.week_index_in_macro === targetIdx; });
    }

    // ----- Week navigation ---------------------------------------------------
    function navigateWeek(delta) {
        if (!state.currentMicro || !state.macrocycle) return;
        const nextMicro = findAdjacentMicro(state.currentMicro, delta);
        if (!nextMicro) {
            CHOS.toast.info(delta < 0 ? "Essa é a primeira semana do macro." : "Essa é a última semana do macro.");
            return;
        }
        state.currentMicro = nextMicro;
        state.viewDate = parseISODate(nextMicro.start_date);
        renderWeek();
    }

    function goToToday() {
        if (!state.macrocycle) return;
        const today = new Date();
        const target = state.macrocycle.microcycles.find(function (m) {
            const s = parseISODate(m.start_date), e = parseISODate(m.end_date);
            return today >= s && today <= e;
        });
        if (!target) { CHOS.toast.info("Hoje está fora do macrociclo ativo."); return; }
        state.currentMicro = target;
        state.viewDate = parseISODate(target.start_date);
        renderWeek();
    }

    // ----- Macrocycle creation ----------------------------------------------
    function refreshBlockPlanPreview() {
        const method = document.getElementById("macro-input-methodology").value;
        const plan = METHODOLOGY_PLANS[method] || [];
        const startStr = document.getElementById("macro-input-start").value;
        const start = startStr ? parseISODate(startStr) : mondayOf(new Date());
        if (!startStr) {
            document.getElementById("block-plan-preview").innerHTML = '<div class="text-muted">Informe a data de início.</div>';
            return;
        }
        let html = "", cursor = new Date(start), weekIdx = 0;
        if (!plan.length) {
            html = '<div class="text-muted">Custom: você pode adicionar blocos manualmente após criar.</div>';
        } else {
            plan.forEach(function (b) {
                const blockStart = new Date(cursor);
                const blockEnd = addDays(cursor, b.weeks * 7 - 1);
                cursor = addDays(blockEnd, 1);
                weekIdx += b.weeks;
                html += `<div class="mb-1">
                    <span class="chos-badge chos-badge-primary">${b.type}</span>
                    <span class="text-muted ms-2">${b.weeks} sem</span>
                    <span class="text-muted ms-2">${formatLongPt(blockStart)} – ${formatLongPt(blockEnd)}</span>
                </div>`;
            });
            html += `<div class="mt-2 fw-bold">Total: ${weekIdx} semanas</div>`;
        }
        document.getElementById("block-plan-preview").innerHTML = html;
    }

    function showCreateMacrocycle() {
        // If an active macrocycle exists, ask what to do
        if (state.macrocycle) {
            const end = parseISODate(state.macrocycle.end_date);
            document.getElementById("confirm-macro-name").textContent = state.macrocycle.name;
            document.getElementById("confirm-macro-dates").textContent =
                formatLongPt(parseISODate(state.macrocycle.start_date)) +
                " – " + formatLongPt(end);
            // Pre-compute the posterior start date (day after current ends)
            const posteriorStart = addDays(end, 1);
            document.getElementById("btn-macro-posterior").dataset.posteriorDate = toISODate(posteriorStart);
            new bootstrap.Modal("#macroConfirmModal").show();
            return;
        }
        // No active macrocycle — open directly
        refreshBlockPlanPreview();
        new bootstrap.Modal("#createMacroModal").show();
    }

    function openCreateMacroPosterior() {
        const posteriorDate = document.getElementById("btn-macro-posterior").dataset.posteriorDate;
        document.getElementById("macro-input-start").value = posteriorDate;
        bootstrap.Modal.getInstance("#macroConfirmModal").hide();
        refreshBlockPlanPreview();
        new bootstrap.Modal("#createMacroModal").show();
    }

    function openCreateMacroSubstituir() {
        bootstrap.Modal.getInstance("#macroConfirmModal").hide();
        refreshBlockPlanPreview();
        new bootstrap.Modal("#createMacroModal").show();
    }

    function saveMacrocycle() {
        const name = document.getElementById("macro-input-name").value.trim() || "My Macrocycle";
        const methodology = document.getElementById("macro-input-methodology").value;
        const startStr = document.getElementById("macro-input-start").value;
        const goal = document.getElementById("macro-input-goal").value.trim() || null;
        const minutes = parseInt(document.getElementById("macro-input-minutes").value, 10);
        const days = parseInt(document.getElementById("macro-input-days").value, 10);
        if (!startStr) { CHOS.toast.error("Informe a data de início."); return; }

        const payload = {
            name,
            methodology,
            start_date: startStr,
            goal,
            available_minutes_per_session: minutes,
            training_days_per_week: days,
        };
        const plan = METHODOLOGY_PLANS[methodology];
        if (plan && plan.length) payload.block_plan = plan;

        CHOS.loading.button("#btn-save-macro", true);
        CHOS.api.post("/api/v1/schedule/macrocycles", payload)
            .done(function () {
                CHOS.toast.success("Macrociclo criado!");
                bootstrap.Modal.getInstance("#createMacroModal").hide();
                loadActiveMacro();
            })
            .fail(function (xhr) {
                CHOS.toast.error(xhr.responseJSON?.detail || "Erro ao criar macrociclo.");
            })
            .always(function () { CHOS.loading.button("#btn-save-macro", false); });
    }

    // ----- Toggle rest day (mark/unmark a training day as rest) -----------
    function toggleRestDay(isoDate) {
        if (!state.currentMicro) return;
        const allSessions = state.currentMicro.sessions || [];
        const restMarker = allSessions.find(function(s){return s.date === isoDate && s.status === "skipped";});
        if (restMarker) {
            CHOS.api.delete(`/api/v1/schedule/planned-sessions/${restMarker.id}`)
                .done(function(){ loadActiveMacro(); })
                .fail(function(){ CHOS.toast.error("Erro ao remover descanso."); });
        } else {
            CHOS.api.post("/api/v1/schedule/planned-sessions", {
                microcycle_id: state.currentMicro.id,
                date: isoDate,
                order_in_day: 1,
                shift: "morning",
                duration_minutes: 0,
                workout_type: "rest",
                focus: "Descanso",
                status: "skipped",
            })
                .done(function(){ loadActiveMacro(); })
                .fail(function(){ CHOS.toast.error("Erro ao marcar descanso."); });
        }
    }

    // ----- Day drawer (CRUD sessions) ---------------------------------------
    function openDayDrawer(isoDate) {
        if (!state.currentMicro) return;
        state.drawerDate = isoDate;
        const d = parseISODate(isoDate);
        document.getElementById("drawer-title").textContent = formatLongPt(d);

        const allSessions = state.currentMicro.sessions || [];
        const existing = allSessions.filter(function (s) { return s.date === isoDate; });
        existing.sort(function (a, b) { return a.order_in_day - b.order_in_day; });
        state.drawerSessions = existing.map(function (s) {
            return { ...s, _isNew: false, _deleted: false };
        });
        renderDrawerSessions();
        new bootstrap.Modal("#dayDrawer").show();
    }

    // ----- Template loading (with cache) --------------------------------
    function getTemplate(templateId) {
        return state.templateCache[templateId] || null;
    }

    function loadTemplate(templateId) {
        if (!templateId || state.templateCache[templateId]) return;
        CHOS.api.get(`/api/v1/training/templates/${templateId}`).then(function(data) {
            state.templateCache[templateId] = data;
            renderDrawerSessions(); // re-render with loaded template
        }).catch(function(err) {
            console.error("Failed to load template", templateId, err);
        });
    }

    function renderMovements(movements) {
        if (!movements || !movements.length) return '<div class="text-muted small fst-italic">Sem movimentos definidos</div>';
        return movements.map(function(m) {
            const sets = m.sets ? `<span class="badge bg-secondary">${m.sets}x</span>` : '';
            const reps = m.reps ? `<span>${m.reps} ${m.reps_unit || ''}</span>` : '';
            const weight = m.weight_kg ? `<span class="text-muted">@ ${m.weight_kg}kg</span>` : '';
            const duration = m.duration_seconds ? `<span class="text-muted">${m.duration_seconds}s</span>` : '';
            const rest = m.rest ? `<span class="text-muted small">rest: ${m.rest}</span>` : '';
            const intensity = m.intensity ? `<span class="badge bg-info">${m.intensity}</span>` : '';
            const notes = m.notes ? `<div class="text-muted small">${m.notes}</div>` : '';
            return `<div class="d-flex align-items-center gap-2 flex-wrap">
                <span class="fw-bold">${m.movement}</span>
                ${sets} ${reps} ${weight} ${duration} ${intensity} ${rest}
                ${notes}
            </div>`;
        }).join('');
    }

    function renderWorkoutDetail(template) {
        const movementsHtml = renderMovements(template.movements || []);
        const warmup = template.warm_up || template.warmup || '';
        const stimulus = template.target_stimulus || '';
        const equipment = (template.equipment_required || []).join(', ') || 'Nenhum';
        return `
            <div class="mt-2 p-2 bg-light rounded" style="border-left: 3px solid #0d6efd;">
                ${template.description ? `<div class="mb-2 text-muted small">${template.description}</div>` : ''}
                ${stimulus ? `<div class="mb-1"><span class="fw-bold small">Stimulus:</span> <span class="text-muted small">${stimulus}</span></div>` : ''}
                ${warmup ? `<div class="mb-1"><span class="fw-bold small">Aquecimento:</span> <span class="text-muted small">${warmup}</span></div>` : ''}
                <div class="mb-1"><span class="fw-bold small">Equipamento:</span> <span class="text-muted small">${equipment}</span></div>
                <div class="mb-1"><span class="fw-bold small">Dificuldade:</span> <span class="badge bg-secondary">${template.difficulty_level || 'rx'}</span></div>
                <div class="mt-2"><span class="fw-bold small">Movimentos:</span></div>
                <div class="ms-2">${movementsHtml}</div>
            </div>`;
    }

    function renderDrawerSessions() {
        const container = document.getElementById("drawer-sessions");
        if (!state.drawerSessions.length) {
            container.innerHTML = '<div class="text-muted fst-italic">Nenhuma sessão planejada — adicione abaixo.</div>';
            return;
        }
        let html = "";
        state.drawerSessions.forEach(function (s, idx) {
            if (s._deleted) return;
            const template = s.generated_template_id ? getTemplate(s.generated_template_id) : null;
            const templateLoading = s.generated_template_id && !state.templateCache[s.generated_template_id];
            const workoutDetail = template ? renderWorkoutDetail(template) : '';
            const loadingSpinner = templateLoading ? '<div class="spinner-border spinner-border-sm text-primary ms-2" role="status"></div>' : '';
            html += `
                <div class="chos-card mb-2" data-idx="${idx}">
                    <div class="card-body p-2">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span class="fw-bold">Sessão ${s.order_in_day} ${loadingSpinner}</span>
                            <button class="chos-btn chos-btn-sm chos-btn-outline" onclick="ScheduleUI.deleteSessionRow(${idx})">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                        ${workoutDetail}
                        <div class="row g-2 mt-1">
                            <div class="col-md-3">
                                <label class="chos-label small">Shift</label>
                                <select class="form-select form-select-sm" data-field="shift">
                                    ${["morning","afternoon","evening","custom"].map(function(v){return `<option value="${v}" ${s.shift===v?"selected":""}>${SHIFT_LABELS[v]}</option>`;}).join("")}
                                </select>
                            </div>
                            <div class="col-md-3">
                                <label class="chos-label small">Hora</label>
                                <input type="time" class="form-control form-control-sm" data-field="start_time" value="${s.start_time ? s.start_time.slice(0,5) : ""}">
                            </div>
                            <div class="col-md-3">
                                <label class="chos-label small">Duração</label>
                                <input type="number" class="form-control form-control-sm" data-field="duration_minutes" min="15" max="240" step="5" value="${s.duration_minutes || 60}">
                            </div>
                            <div class="col-md-3">
                                <label class="chos-label small">Tipo</label>
                                <select class="form-select form-select-sm" data-field="workout_type">
                                    ${["strength","metcon","skill","conditioning","mixed"].map(function(v){return `<option value="${v}" ${s.workout_type===v?"selected":""}>${v}</option>`;}).join("")}
                                </select>
                            </div>
                            <div class="col-12">
                                <label class="chos-label small">Foco</label>
                                <input type="text" class="form-control form-control-sm" data-field="focus" value="${s.focus || ""}" placeholder="Ex: heavy back squat + short metcon">
                            </div>
                        </div>
                    </div>
                </div>`;
        });
        container.innerHTML = html;

        // Kick off template loads for any session that has a generated_template_id
        state.drawerSessions.forEach(function(s) {
            if (s.generated_template_id && !state.templateCache[s.generated_template_id]) {
                loadTemplate(s.generated_template_id);
            }
        });

        // Auto-save on field change
        container.querySelectorAll("[data-field]").forEach(function (el) {
            el.addEventListener("change", function (e) {
                const wrapper = e.target.closest("[data-idx]");
                const idx = parseInt(wrapper.dataset.idx, 10);
                const field = e.target.dataset.field;
                let value = e.target.value;
                if (field === "duration_minutes") value = parseInt(value, 10);
                state.drawerSessions[idx][field] = value || null;
                persistSession(state.drawerSessions[idx]);
            });
        });
    }

    function addSessionRow() {
        const usedOrders = state.drawerSessions.filter(function(s){return !s._deleted;}).map(function(s){return s.order_in_day;});
        let nextOrder = 1;
        while (usedOrders.includes(nextOrder) && nextOrder <= 5) nextOrder++;
        if (nextOrder > 5) { CHOS.toast.warning("Máximo de 5 sessões por dia."); return; }

        const newSession = {
            date: state.drawerDate,
            order_in_day: nextOrder,
            shift: "morning",
            start_time: "06:00",
            duration_minutes: 60,
            workout_type: "mixed",
            focus: "",
            _isNew: true,
            _deleted: false,
        };
        state.drawerSessions.push(newSession);
        const payload = {
            date: newSession.date,
            order_in_day: newSession.order_in_day,
            shift: newSession.shift,
            start_time: newSession.start_time,
            duration_minutes: newSession.duration_minutes,
            workout_type: newSession.workout_type,
            focus: null,
        };
        CHOS.api.post(`/api/v1/schedule/microcycles/${state.currentMicro.id}/sessions`, payload)
            .done(function (created) {
                Object.assign(newSession, created, { _isNew: false });
                renderDrawerSessions();
                renderWeek();
            })
            .fail(function (xhr) {
                CHOS.toast.error(xhr.responseJSON?.detail || "Erro ao adicionar sessão.");
                state.drawerSessions = state.drawerSessions.filter(function (s) { return s !== newSession; });
                renderDrawerSessions();
            });
    }

    function deleteSessionRow(idx) {
        const s = state.drawerSessions[idx];
        if (!s.id) {
            state.drawerSessions.splice(idx, 1);
            renderDrawerSessions();
            return;
        }
        if (!confirm("Excluir essa sessão?")) return;
        CHOS.api.delete(`/api/v1/schedule/planned-sessions/${s.id}`)
            .done(function () {
                s._deleted = true;
                renderDrawerSessions();
                renderWeek();
            })
            .fail(function () { CHOS.toast.error("Erro ao excluir sessão."); });
    }

    function persistSession(session) {
        if (!session.id) return;
        const payload = {
            shift: session.shift,
            start_time: session.start_time,
            duration_minutes: session.duration_minutes,
            workout_type: session.workout_type,
            focus: session.focus || null,
        };
        CHOS.api.patch(`/api/v1/schedule/planned-sessions/${session.id}`, payload)
            .done(function () { renderWeek(); })
            .fail(function () { CHOS.toast.error("Erro ao salvar sessão."); });
    }

    // ----- Generate / copy ---------------------------------------------------
    function generateWeek() {
        if (!state.currentMicro) return;
        CHOS.loading.button("#btn-generate-week", true);
        CHOS.api.post(`/api/v1/schedule/microcycles/${state.currentMicro.id}/generate`, {})
            .done(function (data) {
                CHOS.toast.success(`Gerou ${data.generated_sessions} treino(s)!`);
                renderWeek();
            })
            .fail(function (xhr) {
                CHOS.toast.error(xhr.responseJSON?.detail || "Erro ao gerar treinos.");
            })
            .always(function () { CHOS.loading.button("#btn-generate-week", false); });
    }

    function copyFromPreviousWeek() {
        if (!state.currentMicro) return;
        const prev = findAdjacentMicro(state.currentMicro, -1);
        if (!prev) return;
        if (!confirm("Copiar a estrutura da semana anterior? Isso sobrescreve as sessões desta semana.")) return;
        CHOS.api.post(`/api/v1/schedule/microcycles/${state.currentMicro.id}/copy-from/${prev.id}`, {})
            .done(function () { CHOS.toast.success("Copiado!"); renderWeek(); })
            .fail(function () { CHOS.toast.error("Erro ao copiar."); });
    }

    return {
        init: init,
        navigateWeek: navigateWeek,
        goToToday: goToToday,
        showCreateMacrocycle: showCreateMacrocycle,
        saveMacrocycle: saveMacrocycle,
        refreshBlockPlanPreview: refreshBlockPlanPreview,
        openDayDrawer: openDayDrawer,
        toggleRestDay: toggleRestDay,
        addSessionRow: addSessionRow,
        deleteSessionRow: deleteSessionRow,
        generateWeek: generateWeek,
        copyFromPreviousWeek: copyFromPreviousWeek,
    };
})();

// Expose the functions invoked from inline onclick handlers in schedule.html
function navigateWeek(d) { return ScheduleUI.navigateWeek(d); }
function goToToday() { return ScheduleUI.goToToday(); }
function showCreateMacrocycle() { return ScheduleUI.showCreateMacrocycle(); }
function saveMacrocycle() { return ScheduleUI.saveMacrocycle(); }
function refreshBlockPlanPreview() { return ScheduleUI.refreshBlockPlanPreview(); }
function toggleRestDay(iso) { return ScheduleUI.toggleRestDay(iso); }
function addSessionRow() { return ScheduleUI.addSessionRow(); }
function generateWeek() { return ScheduleUI.generateWeek(); }
function copyFromPreviousWeek() { return ScheduleUI.copyFromPreviousWeek(); }
