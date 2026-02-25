/**
 * CrossFit Health OS - Core Utilities
 * Toast notifications, loading states, auth middleware, API helpers
 */

const CHOS = {
   
   // ============================================
   // Auth Middleware
   // ============================================
   auth: {
      getToken() {
         return localStorage.getItem('access_token');
      },
      
      getUser() {
         try {
            return JSON.parse(localStorage.getItem('user') || '{}');
         } catch { return {}; }
      },
      
      isAuthenticated() {
         return !!this.getToken();
      },
      
      requireAuth() {
         if (!this.isAuthenticated()) {
            window.location.href = '/login';
            return false;
         }
         return true;
      },
      
      logout() {
         const token = this.getToken();
         $.ajax({
            url: '/api/v1/auth/logout',
            type: 'POST',
            headers: { 'Authorization': 'Bearer ' + token },
            complete: function() {
               localStorage.removeItem('access_token');
               localStorage.removeItem('user');
               window.location.href = '/';
            }
         });
      }
   },
   
   // ============================================
   // Toast Notifications
   // ============================================
   toast: {
      _container: null,
      
      _getContainer() {
         if (!this._container) {
            this._container = document.createElement('div');
            this._container.className = 'chos-toast-container';
            document.body.appendChild(this._container);
         }
         return this._container;
      },
      
      show(message, type = 'info', duration = 4000) {
         const container = this._getContainer();
         const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
         };
         
         const colors = {
            success: 'color: var(--color-success)',
            error: 'color: var(--color-danger)',
            warning: 'color: var(--color-warning)',
            info: 'color: var(--color-primary)'
         };
         
         const toast = document.createElement('div');
         toast.className = 'chos-toast ' + type;
         toast.innerHTML = `
            <i class="fas ${icons[type] || icons.info}" style="${colors[type] || colors.info}; font-size: 1.25rem;"></i>
            <div style="flex: 1;">
               <div style="font-weight: 600; font-size: 0.875rem;">${message}</div>
            </div>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; cursor: pointer; color: var(--color-text-muted); font-size: 1.25rem;">
               <i class="fas fa-times"></i>
            </button>
         `;
         
         container.appendChild(toast);
         
         if (duration > 0) {
            setTimeout(() => {
               toast.style.animation = 'slideOutRight 0.3s ease-in forwards';
               setTimeout(() => toast.remove(), 300);
            }, duration);
         }
         
         return toast;
      },
      
      success(msg) { return this.show(msg, 'success'); },
      error(msg) { return this.show(msg, 'error', 6000); },
      warning(msg) { return this.show(msg, 'warning'); },
      info(msg) { return this.show(msg, 'info'); }
   },
   
   // ============================================
   // Loading States
   // ============================================
   loading: {
      button(btn, loading = true) {
         const $btn = $(btn);
         if (loading) {
            $btn.addClass('loading').prop('disabled', true);
            if (!$btn.find('.btn-spinner').length) {
               $btn.wrapInner('<span class="btn-text"></span>');
               $btn.prepend('<span class="btn-spinner"><i class="fas fa-spinner fa-spin"></i></span> ');
            }
         } else {
            $btn.removeClass('loading').prop('disabled', false);
         }
      },
      
      skeleton(container, count = 3) {
         const $container = $(container);
         let html = '';
         for (let i = 0; i < count; i++) {
            html += `
               <div class="chos-card mb-3">
                  <div class="card-body">
                     <div class="chos-skeleton chos-skeleton-title"></div>
                     <div class="chos-skeleton chos-skeleton-text" style="width: 80%;"></div>
                     <div class="chos-skeleton chos-skeleton-text" style="width: 60%;"></div>
                  </div>
               </div>
            `;
         }
         $container.html(html);
      },
      
      spinner(container) {
         $(container).html(`
            <div class="text-center py-5">
               <div class="spinner-border text-primary" role="status">
                  <span class="visually-hidden">Loading...</span>
               </div>
               <p class="text-muted mt-3">Loading...</p>
            </div>
         `);
      }
   },
   
   // ============================================
   // API Helper
   // ============================================
   api: {
      _baseHeaders() {
         const headers = { 'Content-Type': 'application/json' };
         const token = CHOS.auth.getToken();
         if (token) headers['Authorization'] = 'Bearer ' + token;
         return headers;
      },
      
      get(url) {
         return $.ajax({
            url: url,
            type: 'GET',
            headers: this._baseHeaders(),
            dataType: 'json'
         }).fail(this._handleError);
      },
      
      post(url, data) {
         return $.ajax({
            url: url,
            type: 'POST',
            headers: this._baseHeaders(),
            data: JSON.stringify(data),
            dataType: 'json'
         }).fail(this._handleError);
      },
      
      patch(url, data) {
         return $.ajax({
            url: url,
            type: 'PATCH',
            headers: this._baseHeaders(),
            data: JSON.stringify(data),
            dataType: 'json'
         }).fail(this._handleError);
      },
      
      delete(url) {
         return $.ajax({
            url: url,
            type: 'DELETE',
            headers: this._baseHeaders()
         }).fail(this._handleError);
      },
      
      _handleError(xhr) {
         if (xhr.status === 401) {
            CHOS.toast.error('Session expired. Please login again.');
            setTimeout(() => { window.location.href = '/login'; }, 1500);
         } else if (xhr.status === 422) {
            const errors = xhr.responseJSON?.detail;
            if (Array.isArray(errors)) {
               errors.forEach(e => CHOS.toast.error(e.msg));
            } else {
               CHOS.toast.error('Validation error');
            }
         } else if (xhr.status >= 500) {
            CHOS.toast.error('Server error. Please try again later.');
         }
      }
   },
   
   // ============================================
   // Formatters
   // ============================================
   format: {
      date(dateStr) {
         return new Date(dateStr).toLocaleDateString('pt-BR', {
            day: '2-digit', month: '2-digit', year: 'numeric'
         });
      },
      
      dateTime(dateStr) {
         return new Date(dateStr).toLocaleDateString('pt-BR', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
         });
      },
      
      relativeTime(dateStr) {
         const now = new Date();
         const then = new Date(dateStr);
         const diff = Math.floor((now - then) / 1000);
         
         if (diff < 60) return 'agora';
         if (diff < 3600) return Math.floor(diff / 60) + 'min atrás';
         if (diff < 86400) return Math.floor(diff / 3600) + 'h atrás';
         if (diff < 604800) return Math.floor(diff / 86400) + 'd atrás';
         return this.date(dateStr);
      },
      
      rpeStars(rpe, max = 10) {
         let html = '<span class="chos-rpe">';
         for (let i = 1; i <= max; i++) {
            html += `<i class="fas fa-star star ${i <= rpe ? 'active' : ''}"></i>`;
         }
         html += '</span>';
         return html;
      },
      
      readinessClass(score) {
         if (score >= 80) return 'high';
         if (score >= 50) return 'medium';
         return 'low';
      }
   },
   
   // ============================================
   // Dashboard Init
   // ============================================
   initDashboard() {
      if (!this.auth.requireAuth()) return;
      
      const user = this.auth.getUser();
      if (user.name) {
         $('#user-name').text(user.name);
         $('#welcome-name').text(user.name.split(' ')[0]);
      }
      
      // Setup logout
      $('#logout-btn').on('click', function(e) {
         e.preventDefault();
         CHOS.auth.logout();
      });
      
      // Set today's date
      const today = new Date().toLocaleDateString('pt-BR', {
         weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
      });
      $('#today-date').text(today);
   }
};

// Add slideOutRight animation
const style = document.createElement('style');
style.textContent = `
   @keyframes slideOutRight {
      to { transform: translateX(120%); opacity: 0; }
   }
`;
document.head.appendChild(style);

// Global AJAX setup for auth
$.ajaxSetup({
   beforeSend: function(xhr) {
      const token = CHOS.auth.getToken();
      if (token) {
         xhr.setRequestHeader('Authorization', 'Bearer ' + token);
      }
   }
});

// Make CHOS available globally
window.CHOS = CHOS;
