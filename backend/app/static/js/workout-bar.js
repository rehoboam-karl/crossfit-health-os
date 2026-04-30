// Persistent workout bar — Spotify-mini-player style.
// Reads localStorage["chos-active-workout"] = {name, started_at_ms, type}
// and shows a fixed bar with elapsed time + tap-to-return. Cleared from
// localStorage when the user marks the workout complete or hits the X.
(function () {
   const STORAGE_KEY = 'chos-active-workout';
   const bar    = document.getElementById('chos-workout-bar');
   const $title = document.getElementById('chos-workout-bar-title');
   const $time  = document.getElementById('chos-workout-bar-time');
   const $meta  = document.getElementById('chos-workout-bar-meta');
   if (!bar) return;

   let tickInterval = null;

   function read() {
      try {
         const raw = localStorage.getItem(STORAGE_KEY);
         return raw ? JSON.parse(raw) : null;
      } catch (_) { return null; }
   }
   function write(data) {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch (_) {}
      render();
   }
   function clear() {
      try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
      render();
   }

   function fmt(ms) {
      const total = Math.max(0, Math.floor(ms / 1000));
      const h = Math.floor(total / 3600);
      const m = Math.floor((total % 3600) / 60);
      const s = total % 60;
      const pad = n => String(n).padStart(2, '0');
      return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
   }

   function render() {
      const session = read();
      if (!session || !session.started_at_ms) {
         bar.classList.remove('is-visible');
         document.body.classList.remove('has-workout-bar');
         if (tickInterval) { clearInterval(tickInterval); tickInterval = null; }
         return;
      }
      bar.classList.add('is-visible');
      document.body.classList.add('has-workout-bar');
      $title.textContent = session.name || 'Workout';
      $meta.textContent  = session.type ? session.type.toUpperCase() : '';
      const tick = () => { $time.textContent = fmt(Date.now() - session.started_at_ms); };
      tick();
      if (tickInterval) clearInterval(tickInterval);
      tickInterval = setInterval(tick, 1000);
   }

   // Re-render when a different tab changes the storage key (e.g. user has
   // two windows open and starts a workout on one).
   window.addEventListener('storage', (ev) => {
      if (ev.key === STORAGE_KEY) render();
   });

   // Public API for templates to start/clear the active workout.
   window.CHOS = window.CHOS || {};
   window.CHOS.workoutBar = {
      start({ name, type }) {
         write({ name, type: type || null, started_at_ms: Date.now() });
      },
      clear() { clear(); },
      current() { return read(); }
   };

   render();
})();
