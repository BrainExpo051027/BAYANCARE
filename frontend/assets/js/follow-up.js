// Follow-up notification management
async function loadFollowUpNotifications() {
    const container = document.getElementById("bcFollowUpList");
    if (!container) return;
    
    container.innerHTML = '<p class="bc-muted mb-0">Loading notifications…</p>';
    
    try {
        const notifications = await getMyFollowUps();
        if (!notifications || !notifications.length) {
            container.innerHTML = '<p class="bc-muted mb-0">No follow-up notifications.</p>';
            return;
        }
        
        container.innerHTML = notifications.map(n => `
            <div class="bc-announcement-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="fw-semibold">Assessment #${n.assessment_id}</div>
                        <div class="bc-muted small">${new Date(n.notification_date).toLocaleString()}</div>
                        <div class="small mt-1">
                            <strong>Status:</strong> 
                            <span class="badge bg-${n.status === 'IMPROVED' ? 'success' : n.status === 'WORSENED' ? 'danger' : 'warning'}">
                                ${n.status}
                            </span>
                        </div>
                        ${n.user_response ? `<div class="small mt-1"><strong>Your response:</strong> ${n.user_response}</div>` : ''}
                        ${n.auto_referral_generated ? '<div class="small mt-1 text-info"><strong>Auto-referral generated</strong></div>' : ''}
                    </div>
                </div>
            </div>
        `).join('');
        
    } catch (err) {
        console.error(err);
        container.innerHTML = `<p class="text-danger mb-0">Failed to load notifications: ${err.message}</p>`;
    }
}

// Follow-up response modal
async function showFollowUpResponseModal(assessmentId) {
    const modalHtml = `
        <div class="modal fade" id="followUpResponseModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Health Check-in Response</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p class="bc-muted">How are you feeling after your recent assessment?</p>
                        <div class="mb-3">
                            <label class="form-label">Your condition status:</label>
                            <select class="form-select" id="followUpResponse" required>
                                <option value="">Select your status...</option>
                                <option value="IMPROVED">✅ Symptoms have improved</option>
                                <option value="SAME">➡️ Symptoms are the same</option>
                                <option value="WORSENED">⚠️ Symptoms have worsened</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Additional notes (optional):</label>
                            <textarea class="form-control" id="followUpNotes" rows="3" 
                                      placeholder="Describe any changes in your condition..."></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="submitFollowUpResponse">Submit Response</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal
    const existingModal = document.getElementById("followUpResponseModal");
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    
    // Setup form submission
    const submitBtn = document.getElementById("submitFollowUpResponse");
    if (submitBtn) {
        submitBtn.addEventListener("click", async () => {
            const response = document.getElementById("followUpResponse").value;
            const notes = document.getElementById("followUpNotes").value;
            
            if (!response) {
                showToast("Please select your condition status", "warning");
                return;
            }
            
            try {
                const result = await submitFollowUpResponse(assessmentId, response, notes);
                
                if (result.referral_code) {
                    showToast(`Response recorded. Auto-referral generated: ${result.referral_code}`, "success");
                } else {
                    showToast("Response recorded successfully", "success");
                }
                
                // Close modal and refresh notifications
                const modal = bootstrap.Modal.getInstance(document.getElementById("followUpResponseModal"));
                modal.hide();
                loadFollowUpNotifications();
                
            } catch (err) {
                showToast(err.message || "Failed to submit response", "danger");
            }
        });
    }
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById("followUpResponseModal"));
    modal.show();
}

// API call to get follow-up notifications
async function getMyFollowUps() {
    return apiCall("/follow-up/my-notifications");
}

// API call to submit follow-up response
async function submitFollowUpResponse(assessmentId, response, notes) {
    return apiCall("/follow-up/respond", {
        method: "POST",
        body: JSON.stringify({
            assessment_id: assessmentId,
            response: response,
            notes: notes
        })
    });
}
