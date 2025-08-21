// API utility functions for Scout Accelerator
const API = {
    baseURL: 'http://localhost:8001',

    // Token management
    getToken() {
        return localStorage.getItem('access_token');
    },

    setToken(token) {
        localStorage.setItem('access_token', token);
    },

    removeToken() {
        localStorage.removeItem('access_token');
    },

    // Get user info from token
    getUserFromToken() {
        const token = this.getToken();
        if (!token) return null;

        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return {
                user_id: payload.sub,
                email: payload.email,
                role: payload.role
            };
        } catch (error) {
            console.error('Error parsing token:', error);
            return null;
        }
    },

    // Generic API request function
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const token = this.getToken();

        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` }),
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    },

    // Authentication endpoints
    async login(credentials) {
        const response = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify(credentials)
        });

        if (response.access_token) {
            this.setToken(response.access_token);
        }

        return response;
    },

    async signup(userData) {
        const response = await this.request('/auth/signup', {
            method: 'POST',
            body: JSON.stringify(userData)
        });

        if (response.access_token) {
            this.setToken(response.access_token);
        }

        return response;
    },

    // Dashboard endpoints
    async getScoutDashboard() {
        return await this.request('/dashboard/scout');
    },

    async getScoutmasterDashboard() {
        return await this.request('/dashboard/scoutmaster');
    },

    // Requirements endpoints
    async getRequirementsByRank(rank) {
        return await this.request(`/requirements/${rank}`);
    },

    // Sign-off requests
    async createSignoffRequest(requirementId) {
        return await this.request('/signoff-request', {
            method: 'POST',
            body: JSON.stringify({ requirement_id: requirementId })
        });
    },

    // Conference requests
    async createConferenceRequest(type, rank) {
        return await this.request('/conference-request', {
            method: 'POST',
            body: JSON.stringify({ conference_type: type, rank: rank })
        });
    },

    // Troop management endpoints
    async getTroopMembers() {
        return await this.request('/troop/members');
    },

    async updateMember(memberId, updates) {
        return await this.request('/troop/update-member', {
            method: 'POST',
            body: JSON.stringify({ member_id: memberId, updates: updates })
        });
    },

    async removeMember(memberId) {
        return await this.request('/troop/remove-member', {
            method: 'POST',
            body: JSON.stringify({ member_id: memberId })
        });
    },

    async approveSignoff(signoffId) {
        return await this.request('/troop/approve-signoff', {
            method: 'POST',
            body: JSON.stringify({ signoff_id: signoffId })
        });
    },

    async rejectSignoff(signoffId, reason = null) {
        return await this.request('/troop/reject-signoff', {
            method: 'POST',
            body: JSON.stringify({ signoff_id: signoffId, reason: reason })
        });
    },

    async scheduleConference(conferenceId, scheduledDate) {
        return await this.request('/troop/schedule-conference', {
            method: 'POST',
            body: JSON.stringify({ conference_id: conferenceId, scheduled_date: scheduledDate })
        });
    },

    // Check if user is authenticated
    isAuthenticated() {
        const token = this.getToken();
        if (!token) return false;

        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const now = Date.now() / 1000;
            return payload.exp > now;
        } catch (error) {
            return false;
        }
    },

    // Logout
    logout() {
        this.removeToken();
        window.location.href = 'signin.html';
    }
};

// Export for use in other modules
window.API = API;
