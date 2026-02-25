/**
 * CrossFit Health OS - Core Utilities
 * API helpers, auth, and common functions
 */

const CHOS = {
    /**
     * API helper with authentication
     */
    api: {
        /**
         * Make authenticated API request
         */
        request: async function(url, options = {}) {
            const token = localStorage.getItem('access_token');
            
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                    ...(token && { 'Authorization': `Bearer ${token}` })
                }
            };
            
            const mergedOptions = {
                ...defaultOptions,
                ...options,
                headers: {
                    ...defaultOptions.headers,
                    ...(options.headers || {})
                }
            };
            
            try {
                const response = await fetch(url, mergedOptions);
                
                if (response.status === 401) {
                    // Unauthorized - redirect to login
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('user');
                    window.location.href = '/login';
                    throw new Error('Unauthorized');
                }
                
                if (!response.ok) {
                    const error = await response.json().catch(() => ({ detail: response.statusText }));
                    throw new Error(error.detail || `HTTP ${response.status}`);
                }
                
                return await response.json();
            } catch (error) {
                console.error('API request failed:', error);
                throw error;
            }
        },
        
        /**
         * GET request
         */
        get: async function(url) {
            return this.request(url, { method: 'GET' });
        },
        
        /**
         * POST request
         */
        post: async function(url, data) {
            return this.request(url, {
                method: 'POST',
                body: JSON.stringify(data)
            });
        },
        
        /**
         * PATCH request
         */
        patch: async function(url, data) {
            return this.request(url, {
                method: 'PATCH',
                body: JSON.stringify(data)
            });
        },
        
        /**
         * DELETE request
         */
        delete: async function(url) {
            return this.request(url, { method: 'DELETE' });
        }
    },
    
    /**
     * Toast notifications
     */
    toast: {
        show: function(message, type = 'info') {
            const container = document.getElementById('toast-container');
            if (!container) {
                console.warn('Toast container not found');
                return;
            }
            
            const bgClass = type === 'success' ? 'bg-success' : 
                           type === 'error' ? 'bg-danger' : 
                           type === 'warning' ? 'bg-warning' : 'bg-info';
            
            const toast = document.createElement('div');
            toast.className = `toast align-items-center text-white ${bgClass} border-0`;
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');
            
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;
            
            container.appendChild(toast);
            
            const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
            bsToast.show();
            
            toast.addEventListener('hidden.bs.toast', () => {
                toast.remove();
            });
        },
        
        success: function(message) {
            this.show(message, 'success');
        },
        
        error: function(message) {
            this.show(message, 'error');
        },
        
        warning: function(message) {
            this.show(message, 'warning');
        },
        
        info: function(message) {
            this.show(message, 'info');
        }
    },
    
    /**
     * Loading spinner
     */
    loading: {
        show: function() {
            const spinner = document.getElementById('loading-spinner');
            if (spinner) {
                spinner.classList.remove('d-none');
            }
        },
        
        hide: function() {
            const spinner = document.getElementById('loading-spinner');
            if (spinner) {
                spinner.classList.add('d-none');
            }
        }
    },
    
    /**
     * Date/time utilities
     */
    datetime: {
        formatDate: function(dateStr) {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric' 
            });
        },
        
        formatTime: function(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        },
        
        formatDuration: function(minutes) {
            const hrs = Math.floor(minutes / 60);
            const mins = minutes % 60;
            return hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`;
        }
    },
    
    /**
     * Auth helpers
     */
    auth: {
        isAuthenticated: function() {
            return !!localStorage.getItem('access_token');
        },
        
        getUser: function() {
            const userStr = localStorage.getItem('user');
            return userStr ? JSON.parse(userStr) : null;
        },
        
        logout: function() {
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            window.location.href = '/login';
        }
    }
};

// Make CHOS globally available
window.CHOS = CHOS;
