/**
 * API Client for CrossFit Health OS Backend
 */
import axios, { AxiosInstance, AxiosError } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth token to requests
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle token expiration
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired, redirect to login
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // ============================================
  // Auth Endpoints
  // ============================================

  async register(data: {
    email: string;
    password: string;
    confirm_password: string;
    name: string;
    birth_date?: string;
    weight_kg?: number;
    height_cm?: number;
    fitness_level?: string;
    goals?: string[];
  }) {
    const response = await this.client.post('/api/v1/auth/register', data);
    const { access_token, user } = response.data;
    
    // Store token and user
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('user', JSON.stringify(user));
    
    return response.data;
  }

  async login(email: string, password: string) {
    const response = await this.client.post('/api/v1/auth/login', {
      email,
      password,
    });
    
    const { access_token, user } = response.data;
    
    // Store token and user
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('user', JSON.stringify(user));
    
    return response.data;
  }

  async logout() {
    await this.client.post('/api/v1/auth/logout');
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  }

  async forgotPassword(email: string) {
    const response = await this.client.post('/api/v1/auth/forgot-password', {
      email,
    });
    return response.data;
  }

  async resetPassword(token: string, new_password: string, confirm_password: string) {
    const response = await this.client.post('/api/v1/auth/reset-password', {
      token,
      new_password,
      confirm_password,
    });
    return response.data;
  }

  // ============================================
  // User Endpoints
  // ============================================

  async getMe() {
    const response = await this.client.get('/api/v1/users/me');
    return response.data;
  }

  async updateProfile(data: any) {
    const response = await this.client.patch('/api/v1/users/me', data);
    return response.data;
  }

  // ============================================
  // Schedule Endpoints
  // ============================================

  async getActiveSchedule() {
    const response = await this.client.get('/api/v1/schedule/weekly/active');
    return response.data;
  }

  async createSchedule(data: any) {
    const response = await this.client.post('/api/v1/schedule/weekly', data);
    return response.data;
  }

  async generateAIProgram(data: {
    methodology: string;
    week_number: number;
    focus_movements?: string[];
    include_previous_week?: boolean;
  }) {
    const response = await this.client.post('/api/v1/schedule/weekly/generate-ai', data);
    return response.data;
  }

  // ============================================
  // Review Endpoints
  // ============================================

  async submitFeedback(data: any) {
    const response = await this.client.post('/api/v1/review/feedback', data);
    return response.data;
  }

  async generateWeeklyReview(data: {
    week_number: number;
    week_start_date: string;
    week_end_date: string;
    athlete_notes?: string;
  }) {
    const response = await this.client.post('/api/v1/review/weekly', data);
    return response.data;
  }

  async getLatestReview() {
    const response = await this.client.get('/api/v1/review/weekly/latest');
    return response.data;
  }

  // ============================================
  // Training Endpoints
  // ============================================

  async getTodayWorkout() {
    const response = await this.client.get('/api/v1/training/workouts/today');
    return response.data;
  }

  async listSessions(limit = 20) {
    const response = await this.client.get('/api/v1/training/sessions', {
      params: { limit },
    });
    return response.data;
  }

  // Helper method
  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }

  getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  }
}

export const api = new APIClient();
