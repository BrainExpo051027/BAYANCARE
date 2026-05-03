/* API helper functions for BAYANCARE */
const API_BASE = "http://127.0.0.1:5000/api";

async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;

    const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
    const headers = {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(options.headers || {}),
    };

    const response = await fetch(url, {
        credentials: "include",
        headers,
        ...options,
    });

    if (!response.ok) {
        let message = "API error";
        try {
            const contentType = response.headers.get("content-type") || "";
            if (contentType.includes("application/json")) {
                const error = await response.json();
                message = error.error || error.message || message;
            } else {
                if (response.status === 401 || response.status === 403 || response.redirected) {
                    message = "You are not logged in or your session expired. Please log in first.";
                } else if (response.status === 405) {
                    message = "Method not allowed on this endpoint.";
                }
            }
        } catch (e) {
            /* use default message */
        }
        throw new Error(message);
    }

    try {
        return await response.json();
    } catch {
        return null;
    }
}

// Auth
async function registerUser(username, email, password, role = "RESIDENT") {
    return apiCall("/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, email, password, role })
    });
}

async function loginUser(username, password) {
    return apiCall("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password })
    });
}

async function logoutUser() {
    return apiCall("/auth/logout", {
        method: "POST",
        body: JSON.stringify({})
    });
}

async function getCurrentUser() {
    return apiCall("/auth/me");
}

// Announcements
async function getAnnouncements() {
    return apiCall("/announcements");
}

async function createAnnouncement(data) {
    if (typeof FormData !== "undefined" && data instanceof FormData) {
        return apiCall("/announcements", {
            method: "POST",
            body: data,
        });
    }
    return apiCall("/announcements", {
        method: "POST",
        body: JSON.stringify(data),
    });
}

// Assessment
async function submitAssessment(data) {
    return apiCall("/assessments", {
        method: "POST",
        body: JSON.stringify(data)
    });
}

async function deleteAssessment(assessmentId) {
    return apiCall(`/assessments/${assessmentId}`, {
        method: "DELETE"
    });
}

async function getSimilarAssessments(assessmentId) {
    return apiCall(`/assessments/${assessmentId}/similar`);
}

// Profile
async function getProfile(userId) {
    return apiCall(`/profile/${userId}`);
}

async function getMyProfile() {
    return apiCall(`/profile/me`);
}

async function updateMyProfile(data) {
    return apiCall(`/profile/me`, {
        method: "PUT",
        body: JSON.stringify(data)
    });
}

async function updateProfile(userId, data) {
    return apiCall(`/profile/${userId}`, {
        method: "PUT",
        body: JSON.stringify(data)
    });
}

async function getAssessmentHistory(userId) {
    return apiCall(`/profile/${userId}/history`);
}

async function getMyAssessmentHistory() {
    return apiCall(`/profile/me/history`);
}

// Referrals
async function getReferrals(barangay = null) {
    const query = barangay ? `?barangay=${encodeURIComponent(barangay)}` : "";
    return apiCall(`/referrals${query}`);
}

async function generateReferral(assessmentId, data) {
    return apiCall(`/referrals/generate/${assessmentId}`, {
        method: "POST",
        body: JSON.stringify(data)
    });
}
