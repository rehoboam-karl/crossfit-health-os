// Theme toggle. Persists in localStorage. Init runs inline in <head> before
// CSS paints (see base.html) — this script just wires the toggle button and
// reacts to OS-level changes when the user has not chosen explicitly.
(function () {
   const STORAGE_KEY = 'chos-theme';

   function currentTheme() {
      return document.documentElement.getAttribute('data-theme') || 'light';
   }

   function applyTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      try { localStorage.setItem(STORAGE_KEY, theme); } catch (e) { /* private mode */ }
   }

   window.CHOS = window.CHOS || {};
   window.CHOS.theme = {
      get current() { return currentTheme(); },
      toggle() {
         applyTheme(currentTheme() === 'dark' ? 'light' : 'dark');
      },
      set(theme) {
         if (theme !== 'dark' && theme !== 'light') return;
         applyTheme(theme);
      }
   };

   // Wire the navbar toggle button (added in partials/navbar.html)
   document.addEventListener('click', function (ev) {
      const btn = ev.target.closest('[data-action="toggle-theme"]');
      if (!btn) return;
      ev.preventDefault();
      window.CHOS.theme.toggle();
   });

   // If the user has not picked one, follow the OS.
   if (window.matchMedia) {
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      mq.addEventListener && mq.addEventListener('change', function (e) {
         try {
            if (localStorage.getItem(STORAGE_KEY)) return;  // explicit choice wins
         } catch (_) {}
         document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
      });
   }
})();
