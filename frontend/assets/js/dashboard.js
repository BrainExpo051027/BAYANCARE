// BAYANCARE dashboard UI logic
// Uses existing api.js helper functions (API_BASE, apiCall, getAnnouncements, submitAssessment, etc.)

document.addEventListener("DOMContentLoaded", () => {
    const sections = document.querySelectorAll(".bc-page");
    const sidebarNav = document.getElementById("bcSidebarNav");
    const mobileNav = document.getElementById("bcMobileNav");
    const mobileToggle = document.getElementById("bcMobileToggle");
    const mobileMenu = document.getElementById("bcMobileMenu");

    const loadingOverlay = document.getElementById("bcLoadingOverlay");

    const toast = document.getElementById("bcToast");
    const toastBody = document.getElementById("bcToastBody");

    // Logout
    const logoutBtn = document.getElementById("bcLogoutBtn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", async () => {
            try {
                await logoutUser();
            } catch (e) {
                // ignore logout errors
            } finally {
                window.location.href = "/";
            }
        });
    }

    function showToast(message, type = "success") {
        if (!toast || !toastBody) return;
        toastBody.textContent = message;
        toast.className = `bc-toast bc-toast-${type}`;
        toast.classList.add("show");
        setTimeout(() => toast.classList.remove("show"), 3000);
    }

    function setLoading(isLoading) {
        if (!loadingOverlay) return;
        loadingOverlay.style.display = isLoading ? "flex" : "none";
    }

    function activateSection(targetId) {
        sections.forEach((s) => {
            if (s.id === targetId) {
                s.classList.add("active");
            } else {
                s.classList.remove("active");
            }
        });

        [sidebarNav, mobileNav].forEach((nav) => {
            if (!nav) return;
            nav.querySelectorAll("button[data-target]").forEach((btn) => {
                btn.classList.toggle("active", btn.dataset.target === targetId);
            });
        });

        // Load data for the activated section
        if (targetId === "bcBHWAnnouncements") {
            loadBHWAnnouncements();
        } else if (targetId === "bcBHWReferrals") {
            loadBHWReferrals();
        } else if (targetId === "bcBHWUsers") {
            searchUsers();
        }
    }

    function wireNav(root) {
        if (!root) return;
        root.addEventListener("click", (e) => {
            const btn = e.target.closest("button[data-target]");
            if (!btn) return;
            const target = btn.dataset.target;
            if (!target) return;
            activateSection(target);
            if (root === mobileNav && mobileMenu) {
                mobileMenu.style.display = "none";
            }
        });
    }

    wireNav(sidebarNav);
    wireNav(mobileNav);

    if (mobileToggle && mobileMenu) {
        mobileToggle.addEventListener("click", () => {
            mobileMenu.style.display = mobileMenu.style.display === "block" ? "none" : "block";
        });
    }

    // Card buttons that navigate sections
    document.body.addEventListener("click", (e) => {
        const btn = e.target.closest("button[data-target]");
        if (!btn) return;
        const target = btn.dataset.target;
        if (!target) return;
        activateSection(target);
    });

    // Symptom multi-step form
    const form = document.getElementById("bcSymptomForm");
    const steps = form ? form.querySelectorAll(".bc-symptom-step") : [];
    let currentStep = 0;
    const stepLabel = document.getElementById("bcStepLabel");
    const prevBtn = document.getElementById("bcPrevStep");
    const nextBtn = document.getElementById("bcNextStep");
    const submitBtn = document.getElementById("bcSubmitAssessment");

    function updateStepControls() {
        if (!steps.length) return;
        steps.forEach((s, i) => {
            s.style.display = i === currentStep ? "block" : "none";
        });
        if (stepLabel) stepLabel.textContent = `${currentStep + 1} of ${steps.length}`;
        if (prevBtn) prevBtn.disabled = currentStep === 0;
        if (nextBtn) nextBtn.style.display = currentStep === steps.length - 1 ? "none" : "inline-flex";
        if (submitBtn) submitBtn.style.display = currentStep === steps.length - 1 ? "inline-flex" : "none";
    }

    if (form && steps.length) {
        updateStepControls();

        nextBtn.addEventListener("click", () => {
            if (currentStep === 0) {
                const ageInput = form.querySelector('input[name="age"]');
                if (ageInput && !ageInput.value) {
                    ageInput.classList.add("is-invalid");
                    ageInput.focus();
                    return;
                }
                ageInput.classList.remove("is-invalid");
            }
            if (currentStep < steps.length - 1) {
                currentStep += 1;
                updateStepControls();
            }
        });

        prevBtn.addEventListener("click", () => {
            if (currentStep > 0) {
                currentStep -= 1;
                updateStepControls();
            }
        });

        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            const age = Number(form.age.value || 0);
            const temperature = form.temperature.value ? Number(form.temperature.value) : null;
            const duration_days = form.duration_days.value ? Number(form.duration_days.value) : null;

            const symptomChecks = form.querySelectorAll(".bc-symptom-check input:checked");
            const symptoms = Array.from(symptomChecks).map((c) => c.value);

            if (form.other_symptoms.value.trim()) {
                symptoms.push(
                    ...form.other_symptoms.value
                        .split(",")
                        .map((s) => s.trim())
                        .filter(Boolean)
                );
            }

            const allergies = form.allergies.value
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean);
            const chronic_conditions = form.chronic_conditions.value
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean);

            const payload = {
                age,
                temperature,
                duration_days,
                symptoms,
                allergies,
                chronic_conditions,
            };

            setLoading(true);

            // Hide any previous results
            const resultPanel = document.getElementById("bcAssessmentResult");
            if (resultPanel) resultPanel.style.display = "none";

            try {
                const data = await submitAssessment(payload);

                // Show results and scroll to them
                renderAssessmentResult(data);

                // Scroll to results
                setTimeout(() => {
                    const resultPanel = document.getElementById("bcAssessmentResult");
                    if (resultPanel) {
                        resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
                    }
                }, 100);

                // Refresh history after successful assessment
                loadHistory();

                showToast("Symptom analysis completed. Risk: " + (data.risk_level || "UNKNOWN"), "success");
            } catch (err) {
                console.error(err);
                showToast(err.message || "An error occurred.", "danger");
            } finally {
                setLoading(false);
            }
        });
    }

    function buildRecommendationsHtml(data) {
        let fullRecommendations = data.recommendations || "";
        const risk = (data.risk_level || "").toUpperCase();

        // For HIGH risk - show CONSULT button instead of auto-referral
        if (risk === "HIGH" && data.consultation_required) {
            const symptomsList = data.symptoms || [];
            const symptomsHtml = symptomsList.length > 0
                ? `<p class="mb-2"><strong>Your symptoms:</strong> ${symptomsList.join(", ")}</p>`
                : '';
            const symptomsJson = JSON.stringify(symptomsList).replace(/"/g, '&quot;');

            fullRecommendations += `
                <div class="alert alert-danger mt-3">
                    <h6><strong>⚠️ HIGH RISK - CONSULTATION REQUIRED</strong></h6>
                    <p class="mb-2">Your assessment shows HIGH RISK. Please request a consultation with a health worker for proper evaluation.</p>
                    ${symptomsHtml}
                    <button id="bcConsultBtn" class="btn btn-lg btn-warning w-100 mt-2" data-assessment-id="${data.assessment_id}" data-symptoms="${symptomsJson}">
                        <i class="bi bi-person-video"></i> REQUEST CONSULTATION
                    </button>
                    <p class="small mt-2 mb-0 text-muted">A BHW will review your case and generate a referral if necessary.</p>
                </div>
            `;

            // Attach click handler after a short delay to ensure DOM is updated
            setTimeout(() => {
                const consultBtn = document.getElementById("bcConsultBtn");
                if (consultBtn) {
                    consultBtn.addEventListener("click", function () {
                        const assessmentId = this.getAttribute("data-assessment-id");
                        const symptomsStr = this.getAttribute("data-symptoms");
                        let symptoms = [];
                        try {
                            symptoms = JSON.parse(symptomsStr);
                        } catch (e) {
                            console.error("Failed to parse symptoms:", e);
                        }
                        requestConsultation(assessmentId, symptoms);
                    });
                }
            }, 100);
        }

        // For existing referral (after consultation is processed)
        if (risk === "HIGH" && data.referral_generated) {
            fullRecommendations += `
                <div class="alert alert-success mt-3">
                    <h6><strong>✅ REFERRAL SLIP GENERATED</strong></h6>
                    <p class="mb-1"><strong>Referral Code:</strong> ${data.referral_code}</p>
                    <p class="mb-1"><strong>Created by:</strong> ${data.referral_created_by_name || data.referral_generated_by || 'BHW / system'}</p>
                    <p class="mb-1">Present this code at the Barangay Health Center or hospital.</p>
                    <a href="/api/referrals/${data.referral_id}/download" class="btn btn-sm btn-success" target="_blank">
                        <i class="bi bi-download"></i> Download Referral PDF
                    </a>
                </div>
            `;
        }

        // For LOW/MODERATE - show home care plan
        if (risk !== "HIGH" && data.home_care_plan) {
            const plan = data.home_care_plan;
            fullRecommendations += `<div class="home-care-plan mt-3">`;
            fullRecommendations += `<h6 class="text-primary"><strong>🏠 HOME CARE PLAN</strong></h6>`;
            fullRecommendations += `<p class="small">${plan.general_advice}</p>`;

            // Medications
            if (plan.medications && plan.medications.length > 0) {
                fullRecommendations += `<div class="mb-2"><strong>💊 Medications:</strong><ul class="small">`;
                plan.medications.forEach(med => {
                    if (med.warning) {
                        fullRecommendations += `<li class="text-warning">⚠️ ${med.warning}</li>`;
                    } else {
                        fullRecommendations += `<li><strong>${med.name}</strong> - ${med.dosage}`;
                        if (med.max_daily) fullRecommendations += `<br><small>${med.max_daily}</small>`;
                        if (med.notes) fullRecommendations += `<br><small class="text-muted">${med.notes}</small>`;
                        fullRecommendations += `</li>`;
                    }
                });
                fullRecommendations += `</ul></div>`;
            }

            // Rest and Recovery
            if (plan.rest_and_recovery) {
                fullRecommendations += `<div class="mb-2"><strong>😴 Rest & Recovery:</strong><ul class="small">`;
                if (plan.rest_and_recovery.sleep) fullRecommendations += `<li>Sleep: ${plan.rest_and_recovery.sleep}</li>`;
                if (plan.rest_and_recovery.activity_level) fullRecommendations += `<li>Activity: ${plan.rest_and_recovery.activity_level}</li>`;
                if (plan.rest_and_recovery.work_school) fullRecommendations += `<li>Work/School: ${plan.rest_and_recovery.work_school}</li>`;
                fullRecommendations += `</ul></div>`;
            }

            // Exercise
            if (plan.exercise) {
                fullRecommendations += `<div class="mb-2"><strong>🚶 Exercise:</strong><ul class="small">`;
                if (plan.exercise.allowed) fullRecommendations += `<li>Allowed: ${plan.exercise.allowed}</li>`;
                if (plan.exercise.avoid) fullRecommendations += `<li>Avoid: ${plan.exercise.avoid}</li>`;
                fullRecommendations += `</ul></div>`;
            }

            // Diet
            if (plan.diet_and_hydration) {
                fullRecommendations += `<div class="mb-2"><strong>🍽️ Diet & Hydration:</strong><ul class="small">`;
                if (plan.diet_and_hydration.fluids) fullRecommendations += `<li>Fluids: ${plan.diet_and_hydration.fluids}</li>`;
                if (plan.diet_and_hydration.foods) fullRecommendations += `<li>Foods: ${plan.diet_and_hydration.foods}</li>`;
                if (plan.diet_and_hydration.avoid) fullRecommendations += `<li>Avoid: ${plan.diet_and_hydration.avoid}</li>`;
                fullRecommendations += `</ul></div>`;
            }

            // Symptom-specific care
            if (plan.symptom_specific_care && plan.symptom_specific_care.length > 0) {
                fullRecommendations += `<div class="mb-2"><strong>🎯 Symptom Care:</strong><ul class="small">`;
                plan.symptom_specific_care.forEach(care => {
                    fullRecommendations += `<li><strong>${care.symptom}:</strong> ${care.care}</li>`;
                });
                fullRecommendations += `</ul></div>`;
            }

            // When to seek care and recovery time
            if (plan.when_to_seek_care) {
                fullRecommendations += `<div class="alert alert-warning small"><strong>⚠️ When to seek medical care:</strong> ${plan.when_to_seek_care}</div>`;
            }
            if (plan.estimated_recovery_time) {
                fullRecommendations += `<p class="small text-muted"><strong>Estimated recovery time:</strong> ${plan.estimated_recovery_time}</p>`;
            }

            fullRecommendations += `</div>`;
        }

        return fullRecommendations;
    }

    function renderAssessmentResult(data) {
        console.log("Rendering assessment result:", data);

        try {
            const panel = document.getElementById("bcAssessmentResult");
            if (!panel) {
                console.error("bcAssessmentResult panel not found!");
                return;
            }

            // Force show the panel
            panel.style.display = "block";
            panel.classList.remove("d-none");

            const badge = document.getElementById("bcRiskBadge");
            const conditionEl = document.getElementById("bcCondition");
            const summaryEl = document.getElementById("bcSummary");
            const recommendEl = document.getElementById("bcRecommendations");
            const confEl = document.getElementById("bcConfidence");
            const confLabelEl = document.getElementById("bcConfidenceLabel");
            const confHelpEl = document.getElementById("bcConfidenceHelp");

            if (!badge || !conditionEl || !summaryEl || !recommendEl || !confEl || !confLabelEl || !confHelpEl) {
                console.error("Missing result elements:", { badge, conditionEl, summaryEl, recommendEl, confEl, confLabelEl, confHelpEl });
                return;
            }

            const risk = (data.risk_level || "").toUpperCase();
            badge.textContent = risk || "UNKNOWN";
            badge.className = "bc-risk-badge";
            if (risk === "LOW") badge.classList.add("bc-risk-low");
            else if (risk === "MODERATE") badge.classList.add("bc-risk-moderate");
            else if (risk === "HIGH") badge.classList.add("bc-risk-high");

            const rawConfidence = typeof data.confidence_score === "number" ? data.confidence_score : null;
            const confidencePct = rawConfidence != null ? Math.round(rawConfidence * 100) : null;
            confEl.textContent = confidencePct != null ? `${confidencePct}%` : "–";

            let confidenceLabel = "";
            let confidenceHelp = "";
            if (rawConfidence == null) {
                confidenceLabel = "";
                confidenceHelp = "";
            } else if (rawConfidence >= 0.85) {
                confidenceLabel = "(High)";
                confidenceHelp = "This result is based on the symptoms you entered. If symptoms worsen, seek professional care.";
            } else if (rawConfidence >= 0.65) {
                confidenceLabel = "(Moderate)";
                confidenceHelp = "This is a guide only. Monitor your symptoms and consult a health worker if there is no improvement.";
            } else {
                confidenceLabel = "(Low)";
                confidenceHelp = "We are not very certain based on the inputs. Consider providing more details or consulting a health worker.";
            }

            confLabelEl.textContent = confidenceLabel ? ` ${confidenceLabel}` : "";
            confHelpEl.textContent = confidenceHelp;
            conditionEl.textContent = data.predicted_condition || "Not specified";
            summaryEl.textContent = data.summary || "";

            recommendEl.innerHTML = buildRecommendationsHtml(data);

            // Load similar assessments after showing results
            if (data.assessment_id) {
                loadSimilarAssessments(data.assessment_id);
            }

        } catch (err) {
            console.error("Error rendering assessment result:", err);
            showToast("Error displaying results. Please check console.", "danger");
        }
    }

    // New Analysis button handler
    const newAnalysisBtn = document.getElementById("bcNewAnalysisBtn");
    if (newAnalysisBtn) {
        newAnalysisBtn.addEventListener("click", () => {
            resetAssessmentForm();
        });
    }

    function resetAssessmentForm() {
        // Reset form fields
        if (form) {
            form.reset();
            // Reset symptom checkboxes
            const checkboxes = form.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(cb => cb.checked = false);
        }

        // Reset to step 1
        currentStep = 0;
        updateStepControls();

        // Hide results panel
        const resultPanel = document.getElementById("bcAssessmentResult");
        if (resultPanel) {
            resultPanel.style.display = "none";
        }

        // Clear similar assessments
        const similarPanel = document.getElementById("bcSimilarAssessments");
        if (similarPanel) {
            similarPanel.innerHTML = "";
        }

        // Scroll to top of form
        const symptomSection = document.getElementById("bcSymptom");
        if (symptomSection) {
            symptomSection.scrollIntoView({ behavior: "smooth", block: "start" });
        }

        showToast("Ready for new analysis", "info");
    }

    // Load similar past assessments
    async function loadSimilarAssessments(assessmentId) {
        const panel = document.getElementById("bcSimilarAssessments");
        if (!panel) return;

        try {
            const data = await getSimilarAssessments(assessmentId);
            if (!data.similar_assessments || data.similar_assessments.length === 0) {
                panel.innerHTML = `<p class="bc-muted small">No similar past assessments found.</p>`;
                return;
            }

            let html = `<h6 class="mt-3"><strong>📋 Similar Past Assessments</strong></h6>`;
            html += `<p class="small bc-muted">You had similar symptoms before. Here's how you managed them:</p>`;

            data.similar_assessments.forEach(sim => {
                const riskClass = sim.risk_level === "HIGH" ? "bc-risk-high" :
                    sim.risk_level === "MODERATE" ? "bc-risk-moderate" : "bc-risk-low";
                html += `
                    <div class="bc-announcement-item small">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <div class="fw-semibold">Assessment #${sim.id} 
                                    <span class="bc-risk-badge ${riskClass}">${sim.risk_level}</span>
                                </div>
                                <div class="bc-muted">${new Date(sim.created_at).toLocaleDateString()}</div>
                                <div class="mt-1"><strong>Matching symptoms:</strong> ${sim.matching_symptoms.join(", ")}</div>
                                <div><strong>What helped:</strong> ${sim.recommendations || "N/A"}</div>
                                ${sim.has_referral ? '<span class="badge bg-info">Had referral</span>' : ''}
                            </div>
                        </div>
                    </div>
                `;
            });

            panel.innerHTML = html;
        } catch (err) {
            console.error("Failed to load similar assessments:", err);
            panel.innerHTML = `<p class="bc-muted small">Could not load similar assessments.</p>`;
        }
    }

    // Track seen announcements for notification count
    let lastSeenAnnouncementId = parseInt(localStorage.getItem('lastSeenAnnouncementId')) || 0;

    // Announcements list
    async function loadAnnouncements() {
        const container = document.getElementById("bcAnnouncementList");
        if (!container) return;
        container.innerHTML = '<div class="bc-skeleton" style="height: 120px; margin-bottom: 15px;"></div><div class="bc-skeleton" style="height: 120px;"></div>';
        try {
            const list = await getAnnouncements();
            if (!list.length) {
                container.innerHTML = '<div class="bc-empty-state"><i class="bi bi-megaphone"></i><h6>No Announcements</h6><p class="small mb-0">There are no community announcements at this time.</p></div>';
                updateNotificationCount(0);
                return;
            }

            // Sort by newest first
            list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

            // Count unseen announcements
            const unseenCount = list.filter(a => !seenAnnouncementIds.includes(a.id)).length;
            updateNotificationCount(unseenCount);

            // Show "View All" button if more than 3 announcements
            const viewAllBtn = document.getElementById("bcViewAllAnnouncements");
            const footer = document.getElementById("bcAnnouncementFooter");
            if (list.length > 3) {
                if (viewAllBtn) viewAllBtn.classList.remove("d-none");
                if (footer) footer.classList.remove("d-none");
            } else {
                if (viewAllBtn) viewAllBtn.classList.add("d-none");
                if (footer) footer.classList.add("d-none");
            }

            // Display first 3 announcements with full content
            const displayList = list.slice(0, 3);

            container.innerHTML = displayList
                .map(
                    (a) => {
                        const isNew = !seenAnnouncementIds.includes(a.id);
                        const eventDatesHtml = (a.event_start_date || a.event_end_date) ? `
                            <div class="mt-2 mb-2">
                                <small class="text-muted" style="font-size: 0.95rem;">
                                    <i class="bi bi-calendar-event"></i> 
                                    ${a.event_start_date ? new Date(a.event_start_date).toLocaleDateString() : 'TBA'} 
                                    ${a.event_end_date ? ' - ' + new Date(a.event_end_date).toLocaleDateString() : ''}
                                </small>
                            </div>
                        ` : '';

                        return `
                        <div class="card mb-3 announcement-card ${isNew ? 'border-primary border-2' : ''}" data-id="${a.id}" onclick="window.markAnnouncementAsSeen(${a.id})">
                            ${a.image_url ? `
                            <div class="announcement-image-container">
                                <img src="${a.image_url}" class="announcement-image" alt="${a.title}">
                            </div>
                            ` : ''}
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
                                    <h4 class="card-title mb-0 fw-bold" style="font-size: 1.2rem;">
                                        ${a.title} 
                                        ${a.is_emergency ? '<span class="badge bg-danger">EMERGENCY</span>' : ''}
                                        ${isNew ? '<span class="badge bg-success">NEW</span>' : ''}
                                    </h4>
                                    <span class="badge bg-primary" style="font-size: 0.85rem;">${a.category || 'General'}</span>
                                </div>
                                ${a.subcategory ? `<span class="badge bg-secondary mb-2" style="font-size: 0.8rem;">${a.subcategory}</span>` : ''}
                                <div class="card-text" style="font-size: 1rem; line-height: 1.6; white-space: pre-wrap;">${a.body}</div>
                                <div class="d-flex justify-content-between align-items-center mt-3 flex-wrap gap-2">
                                    <small class="text-muted" style="font-size: 0.9rem;">
                                        <i class="bi bi-geo-alt"></i> ${a.barangay} | Posted: ${new Date(a.created_at).toLocaleDateString()}
                                    </small>
                                    ${eventDatesHtml}
                                </div>
                                <hr class="my-3">
                                <div class="d-flex justify-content-between align-items-center flex-wrap gap-3">
                                    <div class="d-flex align-items-center gap-4">
                                        <span class="text-muted d-flex align-items-center gap-2" style="font-size: 0.95rem;" title="Views">
                                            <i class="bi bi-eye fs-6"></i> ${a.view_count || 0}
                                        </span>
                                        <button class="btn ${a.user_has_liked ? 'btn-danger' : 'btn-outline-danger'} btn-sm d-flex align-items-center gap-2" 
                                                onclick="event.stopPropagation(); window.toggleLikeAnnouncement(${a.id}, ${!a.user_has_liked}); window.markAnnouncementAsSeen(${a.id});"
                                                title="${a.user_has_liked ? 'Unlike' : 'Like'}">
                                            <i class="bi bi-heart${a.user_has_liked ? '-fill' : ''}"></i>
                                            <span>${a.like_count || 0}</span>
                                        </button>
                                    </div>
                                    <small class="text-muted">By: ${a.creator_name || 'Unknown'}</small>
                                </div>
                            </div>
                        </div>
                    `;
                    }
                )
                .join("");

            // Increment view counts for visible announcements
            displayList.forEach(a => {
                fetch(`${API_BASE}/announcements/${a.id}/view`, { method: 'POST', credentials: 'include' }).catch(() => { });
            });

        } catch (err) {
            console.error(err);
            container.innerHTML = '<p class="text-danger fs-5">Failed to load announcements.</p>';
        }
    }

    // Track seen announcement IDs (stored as JSON array)
    let seenAnnouncementIds = JSON.parse(localStorage.getItem('seenAnnouncementIds')) || [];

    function updateNotificationCount(count) {
        const badge = document.getElementById("notificationCount");
        const bellBtn = document.getElementById("notificationBell");

        if (badge) {
            if (count > 0) {
                badge.textContent = count > 9 ? '9+' : count;
                badge.classList.remove("d-none");
                // Add pulse animation to bell when there are notifications
                if (bellBtn) {
                    bellBtn.classList.add("btn-danger");
                    bellBtn.classList.remove("btn-outline-dark");
                }
            } else {
                badge.classList.add("d-none");
                if (bellBtn) {
                    bellBtn.classList.remove("btn-danger");
                    bellBtn.classList.add("btn-outline-dark");
                }
            }
        }
    }

    function markAnnouncementAsSeen(announcementId) {
        if (!seenAnnouncementIds.includes(announcementId)) {
            seenAnnouncementIds.push(announcementId);
            localStorage.setItem('seenAnnouncementIds', JSON.stringify(seenAnnouncementIds));

            // Update the NEW badge on the card
            const card = document.querySelector(`.announcement-card[data-id="${announcementId}"]`);
            if (card) {
                const newBadge = card.querySelector('.badge.bg-success');
                if (newBadge) newBadge.remove();
                card.classList.remove('border-primary', 'border-2');
            }

            // Recalculate and update count
            recalculateUnseenCount();
        }
    }

    function recalculateUnseenCount() {
        const cards = document.querySelectorAll('.announcement-card');
        let unseenCount = 0;
        cards.forEach(card => {
            const id = parseInt(card.dataset.id);
            if (!seenAnnouncementIds.includes(id)) {
                unseenCount++;
            }
        });
        updateNotificationCount(unseenCount);
    }

    // Expose functions to window for onclick handlers
    window.markAnnouncementAsSeen = markAnnouncementAsSeen;
    window.viewAllAnnouncements = async function () {
        const container = document.getElementById("bcAnnouncementList");
        if (!container) return;

        try {
            const list = await getAnnouncements();
            list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

            container.innerHTML = list
                .map(
                    (a) => {
                        const isNew = !seenAnnouncementIds.includes(a.id);
                        const eventDatesHtml = (a.event_start_date || a.event_end_date) ? `
                            <div class="mt-2 mb-2">
                                <small class="text-muted" style="font-size: 0.95rem;">
                                    <i class="bi bi-calendar-event"></i> 
                                    ${a.event_start_date ? new Date(a.event_start_date).toLocaleDateString() : 'TBA'} 
                                    ${a.event_end_date ? ' - ' + new Date(a.event_end_date).toLocaleDateString() : ''}
                                </small>
                            </div>
                        ` : '';

                        return `
                        <div class="card mb-3 announcement-card ${isNew ? 'border-primary border-2' : ''}" data-id="${a.id}" onclick="window.markAnnouncementAsSeen(${a.id})">
                            ${a.image_url ? `
                            <div class="announcement-image-container">
                                <img src="${a.image_url}" class="announcement-image" alt="${a.title}">
                            </div>
                            ` : ''}
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
                                    <h4 class="card-title mb-0 fw-bold" style="font-size: 1.2rem;">
                                        ${a.title} 
                                        ${a.is_emergency ? '<span class="badge bg-danger">EMERGENCY</span>' : ''}
                                        ${isNew ? '<span class="badge bg-success">NEW</span>' : ''}
                                    </h4>
                                    <span class="badge bg-primary" style="font-size: 0.85rem;">${a.category || 'General'}</span>
                                </div>
                                ${a.subcategory ? `<span class="badge bg-secondary mb-2" style="font-size: 0.8rem;">${a.subcategory}</span>` : ''}
                                <div class="card-text" style="font-size: 1rem; line-height: 1.6; white-space: pre-wrap;">${a.body}</div>
                                <div class="d-flex justify-content-between align-items-center mt-3 flex-wrap gap-2">
                                    <small class="text-muted" style="font-size: 0.9rem;">
                                        <i class="bi bi-geo-alt"></i> ${a.barangay} | Posted: ${new Date(a.created_at).toLocaleDateString()}
                                    </small>
                                    ${eventDatesHtml}
                                </div>
                                <hr class="my-3">
                                <div class="d-flex justify-content-between align-items-center flex-wrap gap-3">
                                    <div class="d-flex align-items-center gap-4">
                                        <span class="text-muted d-flex align-items-center gap-2" style="font-size: 0.95rem;" title="Views">
                                            <i class="bi bi-eye fs-6"></i> ${a.view_count || 0}
                                        </span>
                                        <button class="btn ${a.user_has_liked ? 'btn-danger' : 'btn-outline-danger'} btn-sm d-flex align-items-center gap-2" 
                                                onclick="event.stopPropagation(); window.toggleLikeAnnouncement(${a.id}, ${!a.user_has_liked}); window.markAnnouncementAsSeen(${a.id});"
                                                title="${a.user_has_liked ? 'Unlike' : 'Like'}">
                                            <i class="bi bi-heart${a.user_has_liked ? '-fill' : ''}"></i>
                                            <span>${a.like_count || 0}</span>
                                        </button>
                                    </div>
                                    <small class="text-muted">By: ${a.creator_name || 'Unknown'}</small>
                                </div>
                            </div>
                        </div>
                    `;
                    }
                )
                .join("");

            // Add expanded class for scrolling when viewing all
            container.classList.add("expanded");

            // Hide the "View All" button after showing all
            const footer = document.getElementById("bcAnnouncementFooter");
            const viewAllBtn = document.getElementById("bcViewAllAnnouncements");
            if (footer) footer.classList.add("d-none");
            if (viewAllBtn) viewAllBtn.classList.add("d-none");

            // Increment view counts
            list.forEach(a => {
                fetch(`${API_BASE}/announcements/${a.id}/view`, { method: 'POST', credentials: 'include' }).catch(() => { });
            });
        } catch (err) {
            console.error("Failed to load all announcements:", err);
        }
    };

    async function toggleLikeAnnouncement(id, shouldLike) {
        try {
            const response = await fetch(`${API_BASE}/announcements/${id}/${shouldLike ? 'like' : 'unlike'}`, {
                method: 'POST',
                credentials: 'include'
            });
            const result = await response.json();
            if (response.ok) {
                loadAnnouncements(); // Refresh to update like status
            } else {
                showToast('Error: ' + result.error, 'danger');
            }
        } catch (err) {
            showToast('Error: ' + err.message, 'danger');
        }
    }

    // Expose to global scope for onclick handlers
    window.toggleLikeAnnouncement = toggleLikeAnnouncement;

    const refreshAnnouncementsBtn = document.getElementById("bcRefreshAnnouncements");
    if (refreshAnnouncementsBtn) {
        refreshAnnouncementsBtn.addEventListener("click", loadAnnouncements);
    }

    // Initial state: show dashboard, and load announcements once.
    activateSection("bcDashboard");
    loadAnnouncements();

    // Health Records (Profile + History)
    let currentProfileData = null;

    async function loadProfile() {
        const panel = document.getElementById("bcProfilePanel");
        const formWrap = document.getElementById("bcProfileFormWrap");
        if (!panel) return;
        panel.innerHTML = `
            <div class="bc-skeleton" style="height: 30px; width: 40%; margin-bottom: 20px;"></div>
            <div class="bc-skeleton" style="height: 100px; width: 100%; margin-bottom: 20px;"></div>
            <div class="bc-skeleton" style="height: 100px; width: 100%; margin-bottom: 20px;"></div>
            <div class="bc-skeleton" style="height: 100px; width: 100%;"></div>
        `;
        try {
            const p = await getMyProfile();
            currentProfileData = p;

            // Display profile info in 4 sections matching the barangay form
            panel.innerHTML = `
                <div class="health-profile">
                    <!-- I. PERSONAL IDENTIFICATION -->
                    <div class="profile-section mb-3">
                        <h6 class="section-title text-primary border-bottom pb-1 mb-2">
                            <i class="bi bi-person-vcard"></i> I. PERSONAL IDENTIFICATION
                        </h6>
                        <div class="row g-2 small">
                            <div class="col-12 col-md-6"><strong>Name:</strong> ${p.last_name || ''}${p.last_name && p.first_name ? ', ' : ''}${p.first_name || ''}${p.middle_name ? ' ' + p.middle_name : ''}</div>
                            <div class="col-6 col-md-3"><strong>Age:</strong> ${p.age ?? "N/A"}</div>
                            <div class="col-6 col-md-3"><strong>Sex:</strong> ${p.sex || "N/A"}</div>
                            <div class="col-6 col-md-4"><strong>DOB:</strong> ${p.date_of_birth ? new Date(p.date_of_birth).toLocaleDateString() : "N/A"}</div>
                            <div class="col-6 col-md-4"><strong>Civil Status:</strong> ${p.civil_status || "N/A"}</div>
                            <div class="col-12"><strong>Address:</strong> ${p.address || "N/A"}</div>
                            <div class="col-6 col-md-6"><strong>Contact:</strong> ${p.contact_number || "N/A"}</div>
                            <div class="col-6 col-md-6"><strong>PhilHealth ID:</strong> ${p.philhealth_id || "N/A"}</div>
                        </div>
                    </div>
                    
                    <!-- II. MEDICAL HISTORY & SOCIAL DETERMINANTS -->
                    <div class="profile-section mb-3">
                        <h6 class="section-title text-primary border-bottom pb-1 mb-2">
                            <i class="bi bi-heart-pulse"></i> II. MEDICAL HISTORY & SOCIAL DETERMINANTS
                        </h6>
                        <div class="row g-2 small">
                            <div class="col-6 col-md-4"><strong>Blood Type:</strong> ${p.blood_type || "N/A"}</div>
                            <div class="col-6 col-md-8"><strong>PWD ID:</strong> ${p.pwd_id || "N/A"}</div>
                            <div class="col-12"><strong>Known Allergies:</strong> ${p.allergies || "None"}</div>
                            <div class="col-12"><strong>Chronic Conditions:</strong> ${p.chronic_conditions || "None"}</div>
                            <div class="col-12"><strong>Current Medications:</strong> ${p.current_medications || "None"}</div>
                            <div class="col-12"><strong>Lifestyle (Smoker/Alcohol):</strong> ${p.lifestyle || "N/A"}</div>
                            <div class="col-12"><strong>Household Details:</strong> ${p.household_details || "N/A"}</div>
                        </div>
                    </div>
                    
                    <!-- III. PUBLIC HEALTH PROGRAM STATUS -->
                    <div class="profile-section mb-3">
                        <h6 class="section-title text-primary border-bottom pb-1 mb-2">
                            <i class="bi bi-shield-check"></i> III. PUBLIC HEALTH PROGRAM STATUS
                        </h6>
                        <div class="row g-2 small">
                            <div class="col-12"><strong>COVID-19 Vaccination:</strong> ${p.covid_vaccination || "N/A"}</div>
                            <div class="col-12"><strong>Other Immunizations:</strong> ${p.other_immunizations || "N/A"}</div>
                            <div class="col-12"><strong>Maternal & Child Health Notes:</strong> ${p.maternal_child_health || "N/A"}</div>
                        </div>
                    </div>
                    
                    <!-- IV. EMERGENCY CONTACT INFO & CERTIFICATION -->
                    <div class="profile-section mb-3">
                        <h6 class="section-title text-primary border-bottom pb-1 mb-2">
                            <i class="bi bi-telephone-emergency"></i> IV. EMERGENCY CONTACT INFO & CERTIFICATION
                        </h6>
                        <div class="row g-2 small">
                            <div class="col-12 col-md-6"><strong>Emergency Contact:</strong> ${p.emergency_contact_person || "N/A"}</div>
                            <div class="col-6 col-md-3"><strong>Relationship:</strong> ${p.emergency_contact_relationship || "N/A"}</div>
                            <div class="col-6 col-md-3"><strong>Number:</strong> ${p.emergency_contact_number || "N/A"}</div>
                            <div class="col-6 col-md-6"><strong>Processed By (BHW):</strong> ${p.processed_by_bhw || "N/A"}</div>
                            <div class="col-6 col-md-6"><strong>Date:</strong> ${p.processed_date ? new Date(p.processed_date).toLocaleDateString() : "N/A"}</div>
                        </div>
                    </div>
                </div>
                <div class="mt-3">
                    <button class="btn btn-sm btn-primary" id="bcEditProfileBtn">
                        <i class="bi bi-pencil"></i> Edit Profile
                    </button>
                </div>
            `;

            // Setup edit form (hidden by default)
            if (formWrap) {
                formWrap.innerHTML = createProfileEditForm(p);
                setupProfileEditHandlers();
            }

        } catch (err) {
            console.error(err);
            panel.innerHTML = `<p class="text-danger mb-0">Failed to load profile: ${err.message}</p>`;
        }
    }

    function createProfileEditForm(p) {
        return `
            <form id="bcProfileEditForm" class="d-none">
                <!-- I. PERSONAL IDENTIFICATION -->
                <h6 class="mb-2 text-primary border-bottom pb-1"><i class="bi bi-person-vcard"></i> I. PERSONAL IDENTIFICATION</h6>
                <div class="row g-2 mb-3">
                    <div class="col-12 col-md-4">
                        <label class="form-label small">Last Name</label>
                        <input type="text" class="form-control form-control-sm" name="last_name" value="${p.last_name || ''}" placeholder="Last Name">
                    </div>
                    <div class="col-12 col-md-4">
                        <label class="form-label small">First Name</label>
                        <input type="text" class="form-control form-control-sm" name="first_name" value="${p.first_name || ''}" placeholder="First Name">
                    </div>
                    <div class="col-12 col-md-4">
                        <label class="form-label small">Middle Name</label>
                        <input type="text" class="form-control form-control-sm" name="middle_name" value="${p.middle_name || ''}" placeholder="Middle Name">
                    </div>
                    <div class="col-6 col-md-4">
                        <label class="form-label small">Date of Birth</label>
                        <input type="date" class="form-control form-control-sm" name="date_of_birth" value="${p.date_of_birth || ''}">
                    </div>
                    <div class="col-6 col-md-2">
                        <label class="form-label small">Age</label>
                        <input type="number" class="form-control form-control-sm" name="age" value="${p.age || ''}" placeholder="Age">
                    </div>
                    <div class="col-6 col-md-3">
                        <label class="form-label small">Sex</label>
                        <select class="form-select form-select-sm" name="sex">
                            <option value="" ${!p.sex ? 'selected' : ''}>Select</option>
                            <option value="Male" ${p.sex === 'Male' ? 'selected' : ''}>Male</option>
                            <option value="Female" ${p.sex === 'Female' ? 'selected' : ''}>Female</option>
                            <option value="Other" ${p.sex === 'Other' ? 'selected' : ''}>Other</option>
                        </select>
                    </div>
                    <div class="col-6 col-md-3">
                        <label class="form-label small">Civil Status</label>
                        <select class="form-select form-select-sm" name="civil_status">
                            <option value="" ${!p.civil_status ? 'selected' : ''}>Select</option>
                            <option value="Single" ${p.civil_status === 'Single' ? 'selected' : ''}>Single</option>
                            <option value="Married" ${p.civil_status === 'Married' ? 'selected' : ''}>Married</option>
                            <option value="Widowed" ${p.civil_status === 'Widowed' ? 'selected' : ''}>Widowed</option>
                            <option value="Separated" ${p.civil_status === 'Separated' ? 'selected' : ''}>Separated</option>
                        </select>
                    </div>
                    <div class="col-12">
                        <label class="form-label small">Full Address</label>
                        <textarea class="form-control form-control-sm" name="address" rows="2" placeholder="Street, Barangay, City, Province">${p.address || ''}</textarea>
                    </div>
                    <div class="col-6 col-md-6">
                        <label class="form-label small">Contact Number</label>
                        <input type="text" class="form-control form-control-sm" name="contact_number" value="${p.contact_number || ''}" placeholder="Phone number">
                    </div>
                    <div class="col-6 col-md-6">
                        <label class="form-label small">PhilHealth ID No.</label>
                        <input type="text" class="form-control form-control-sm" name="philhealth_id" value="${p.philhealth_id || ''}" placeholder="PhilHealth ID">
                    </div>
                </div>

                <!-- II. MEDICAL HISTORY & SOCIAL DETERMINANTS -->
                <h6 class="mb-2 text-primary border-bottom pb-1"><i class="bi bi-heart-pulse"></i> II. MEDICAL HISTORY & SOCIAL DETERMINANTS</h6>
                <div class="row g-2 mb-3">
                    <div class="col-6 col-md-3">
                        <label class="form-label small">Blood Type</label>
                        <select class="form-select form-select-sm" name="blood_type">
                            <option value="" ${!p.blood_type ? 'selected' : ''}>Select</option>
                            <option value="A+" ${p.blood_type === 'A+' ? 'selected' : ''}>A+</option>
                            <option value="A-" ${p.blood_type === 'A-' ? 'selected' : ''}>A-</option>
                            <option value="B+" ${p.blood_type === 'B+' ? 'selected' : ''}>B+</option>
                            <option value="B-" ${p.blood_type === 'B-' ? 'selected' : ''}>B-</option>
                            <option value="AB+" ${p.blood_type === 'AB+' ? 'selected' : ''}>AB+</option>
                            <option value="AB-" ${p.blood_type === 'AB-' ? 'selected' : ''}>AB-</option>
                            <option value="O+" ${p.blood_type === 'O+' ? 'selected' : ''}>O+</option>
                            <option value="O-" ${p.blood_type === 'O-' ? 'selected' : ''}>O-</option>
                        </select>
                    </div>
                    <div class="col-6 col-md-5">
                        <label class="form-label small">PWD ID No. (if any)</label>
                        <input type="text" class="form-control form-control-sm" name="pwd_id" value="${p.pwd_id || ''}" placeholder="PWD ID">
                    </div>
                    <div class="col-12">
                        <label class="form-label small">Known Allergies</label>
                        <textarea class="form-control form-control-sm" name="allergies" rows="2" placeholder="e.g., Penicillin, Dust, Seafood">${p.allergies || ''}</textarea>
                    </div>
                    <div class="col-12">
                        <label class="form-label small">Chronic Conditions (e.g., Hypertension, Diabetes, Asthma)</label>
                        <textarea class="form-control form-control-sm" name="chronic_conditions" rows="2" placeholder="e.g., Diabetes, Hypertension, Asthma">${p.chronic_conditions || ''}</textarea>
                    </div>
                    <div class="col-12">
                        <label class="form-label small">Current Medications</label>
                        <textarea class="form-control form-control-sm" name="current_medications" rows="2" placeholder="List current medications">${p.current_medications || ''}</textarea>
                    </div>
                    <div class="col-12">
                        <label class="form-label small">Lifestyle (Smoker/Alcohol)</label>
                        <input type="text" class="form-control form-control-sm" name="lifestyle" value="${p.lifestyle || ''}" placeholder="e.g., Non-smoker, Occasional alcohol">
                    </div>
                    <div class="col-12">
                        <label class="form-label small">Household Details (Water Source/Toilet Facility)</label>
                        <textarea class="form-control form-control-sm" name="household_details" rows="2" placeholder="e.g., Water: Piped, Toilet: Water-sealed">${p.household_details || ''}</textarea>
                    </div>
                </div>

                <!-- III. PUBLIC HEALTH PROGRAM STATUS -->
                <h6 class="mb-2 text-primary border-bottom pb-1"><i class="bi bi-shield-check"></i> III. PUBLIC HEALTH PROGRAM STATUS</h6>
                <div class="row g-2 mb-3">
                    <div class="col-12">
                        <label class="form-label small">COVID-19 Vaccination Status (1st, 2nd, Booster/s)</label>
                        <input type="text" class="form-control form-control-sm" name="covid_vaccination" value="${p.covid_vaccination || ''}" placeholder="e.g., 1st, 2nd, 1st Booster, 2nd Booster">
                    </div>
                    <div class="col-12">
                        <label class="form-label small">Other Immunizations (Flu, Pneumococcal)</label>
                        <input type="text" class="form-control form-control-sm" name="other_immunizations" value="${p.other_immunizations || ''}" placeholder="e.g., Flu 2024, Pneumococcal">
                    </div>
                    <div class="col-12">
                        <label class="form-label small">Maternal & Child Health Notes (Immunization/Nutritional Status)</label>
                        <textarea class="form-control form-control-sm" name="maternal_child_health" rows="2" placeholder="If applicable: Immunization status, nutritional status, etc.">${p.maternal_child_health || ''}</textarea>
                    </div>
                </div>

                <!-- IV. EMERGENCY CONTACT INFO & CERTIFICATION -->
                <h6 class="mb-2 text-primary border-bottom pb-1"><i class="bi bi-telephone-emergency"></i> IV. EMERGENCY CONTACT INFO & CERTIFICATION</h6>
                <div class="row g-2 mb-3">
                    <div class="col-12 col-md-6">
                        <label class="form-label small">Emergency Contact Person</label>
                        <input type="text" class="form-control form-control-sm" name="emergency_contact_person" value="${p.emergency_contact_person || ''}" placeholder="Full name">
                    </div>
                    <div class="col-6 col-md-3">
                        <label class="form-label small">Relationship</label>
                        <input type="text" class="form-control form-control-sm" name="emergency_contact_relationship" value="${p.emergency_contact_relationship || ''}" placeholder="e.g., Parent, Spouse">
                    </div>
                    <div class="col-6 col-md-3">
                        <label class="form-label small">Contact Number</label>
                        <input type="text" class="form-control form-control-sm" name="emergency_contact_number" value="${p.emergency_contact_number || ''}" placeholder="Phone number">
                    </div>
                </div>
                
                <div class="mt-3 d-flex gap-2">
                    <button type="submit" class="btn btn-sm btn-success"><i class="bi bi-check-circle"></i> Save Profile</button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" id="bcCancelEditBtn"><i class="bi bi-x-circle"></i> Cancel</button>
                </div>
            </form>
        `;
    }

    function setupProfileEditHandlers() {
        const editBtn = document.getElementById("bcEditProfileBtn");
        const form = document.getElementById("bcProfileEditForm");
        const cancelBtn = document.getElementById("bcCancelEditBtn");

        if (editBtn && form) {
            editBtn.addEventListener("click", () => {
                form.classList.remove("d-none");
                editBtn.classList.add("d-none");
            });
        }

        if (cancelBtn && form && editBtn) {
            cancelBtn.addEventListener("click", () => {
                form.classList.add("d-none");
                editBtn.classList.remove("d-none");
            });
        }

        if (form) {
            form.addEventListener("submit", async (e) => {
                e.preventDefault();
                const formData = new FormData(form);
                const data = {
                    // I. PERSONAL IDENTIFICATION
                    full_name: formData.get("full_name") || null,
                    last_name: formData.get("last_name") || null,
                    first_name: formData.get("first_name") || null,
                    middle_name: formData.get("middle_name") || null,
                    date_of_birth: formData.get("date_of_birth") || null,
                    age: formData.get("age") ? parseInt(formData.get("age")) : null,
                    sex: formData.get("sex") || null,
                    civil_status: formData.get("civil_status") || null,
                    address: formData.get("address") || null,
                    contact_number: formData.get("contact_number") || null,
                    philhealth_id: formData.get("philhealth_id") || null,
                    // II. MEDICAL HISTORY & SOCIAL DETERMINANTS
                    blood_type: formData.get("blood_type") || null,
                    pwd_id: formData.get("pwd_id") || null,
                    allergies: formData.get("allergies") || null,
                    chronic_conditions: formData.get("chronic_conditions") || null,
                    current_medications: formData.get("current_medications") || null,
                    lifestyle: formData.get("lifestyle") || null,
                    household_details: formData.get("household_details") || null,
                    // III. PUBLIC HEALTH PROGRAM STATUS
                    covid_vaccination: formData.get("covid_vaccination") || null,
                    other_immunizations: formData.get("other_immunizations") || null,
                    maternal_child_health: formData.get("maternal_child_health") || null,
                    // IV. EMERGENCY CONTACT INFO & CERTIFICATION
                    emergency_contact_person: formData.get("emergency_contact_person") || null,
                    emergency_contact_relationship: formData.get("emergency_contact_relationship") || null,
                    emergency_contact_number: formData.get("emergency_contact_number") || null
                };

                try {
                    await updateMyProfile(data);
                    showToast("Profile updated successfully!", "success");
                    loadProfile(); // Reload to show updated data
                } catch (err) {
                    console.error(err);
                    showToast("Failed to update profile: " + (err.message || "Unknown error"), "danger");
                }
            });
        }
    }

    function riskBadgeClass(risk) {
        const r = (risk || "").toUpperCase();
        if (r === "HIGH") return "bc-risk-high";
        if (r === "MODERATE") return "bc-risk-moderate";
        return "bc-risk-low";
    }

    async function loadHistory() {
        const listEl = document.getElementById("bcHistoryList");
        if (!listEl) return;
        listEl.innerHTML = '<div class="bc-skeleton" style="height: 100px; width: 100%; margin-bottom: 15px;"></div><div class="bc-skeleton" style="height: 100px; width: 100%;"></div>';
        try {
            const items = await getMyAssessmentHistory();
            if (!items || !items.length) {
                listEl.innerHTML = '<div class="bc-empty-state"><i class="bi bi-clock-history"></i><h6>No Assessment History</h6><p class="small mb-0">You have not completed any health assessments yet.</p></div>';
                return;
            }

            listEl.innerHTML = items
                .map(
                    (a) => {
                        // Check for referral info from assessment data
                        const hasReferral = a.referral_id || a.referral_code;

                        // Build action buttons HTML - removed check-in buttons (only in recovery tracking now)
                        let actionButtonsHtml = '';

                        if (hasReferral) {
                            actionButtonsHtml = `
                                <span class="badge bg-danger mb-2 w-100 py-2"><i class="bi bi-hospital"></i> REFERRAL GENERATED</span>
                                <button class="btn btn-sm btn-outline-danger w-100 mb-2" onclick="viewReferralSlip(${a.referral_id}, '${a.referral_code}')">
                                    <i class="bi bi-file-text"></i> View Referral
                                </button>
                            `;
                        } else if (a.status === 'RESOLVED') {
                            actionButtonsHtml = `<span class="badge bg-success mb-2 w-100 py-2"><i class="bi bi-check-circle"></i> COMPLETED</span>`;
                        } else if (a.status === 'REFERRED') {
                            actionButtonsHtml = `<span class="badge bg-danger mb-2 w-100 py-2"><i class="bi bi-hospital"></i> NEEDS REFERRAL</span>`;
                        }

                        return `
                    <div class="bc-announcement-item">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <div class="fw-semibold">Assessment #${a.id}</div>
                                <div class="bc-muted small">${new Date(a.created_at).toLocaleString()}</div>
                                <div class="small mt-1"><strong>Summary:</strong> ${a.assessment_summary || ""}</div>
                                <div class="small"><strong>Symptoms:</strong> ${(a.symptoms || []).join(", ") || "N/A"}</div>
                            </div>
                            <div class="text-end ms-3" style="min-width: 120px;">
                                <span class="bc-risk-badge ${riskBadgeClass(a.risk_level)}">${(a.risk_level || "").toUpperCase()}</span>
                                <div class="mt-2">
                                    ${actionButtonsHtml}
                                </div>
                                <div class="d-flex gap-1 justify-content-end mt-2">
                                    <button class="btn btn-sm btn-outline-info" data-action="review-assessment" data-id="${a.id}" title="Review home care plan">
                                        <i class="bi bi-eye"></i> Review Plan
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" data-action="delete-assessment" data-id="${a.id}" title="Delete assessment">
                                        <i class="bi bi-trash"></i> Delete
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                    }
                )
                .join("");

            // Update dashboard "Monitoring Status" card — date AND risk badge
            const last = items[0];
            const lastEl = document.getElementById("bcLastAssessment");
            if (lastEl) lastEl.textContent = new Date(last.created_at).toLocaleDateString();

            const monitoringBadge = document.getElementById("bcMonitoringBadge");
            if (monitoringBadge && last.risk_level) {
                const risk = (last.risk_level || "").toUpperCase();
                monitoringBadge.textContent = risk || "–";
                monitoringBadge.className = "bc-risk-badge";
                if (risk === "HIGH") monitoringBadge.classList.add("bc-risk-high");
                else if (risk === "MODERATE") monitoringBadge.classList.add("bc-risk-moderate");
                else monitoringBadge.classList.add("bc-risk-low");
            }
        } catch (err) {
            console.error(err);
            listEl.innerHTML = `<p class="text-danger mb-0">Failed to load history: ${err.message}</p>`;
        }
    }

    const refreshHistoryBtn = document.getElementById("bcRefreshHistory");
    if (refreshHistoryBtn) {
        refreshHistoryBtn.addEventListener("click", loadHistory);
    }

    // Load records once on page load
    loadCurrentUser();
    loadProfile();
    loadHistory();

    // Load current user info
    async function loadCurrentUser() {
        try {
            console.log("Loading current user...");

            // Fallback if getCurrentUser is not defined
            if (typeof getCurrentUser === 'undefined') {
                console.log("getCurrentUser not defined, using fallback");
                const user = await apiCall("/auth/me");
                console.log("Current user (fallback):", user);

                const roleEl = document.getElementById("bcUserRole");
                if (roleEl) {
                    roleEl.textContent = user.role || "Resident";
                    console.log("Updated role display to:", user.role);
                }

                if (user.role === "ADMIN") {
                    console.log("User is ADMIN, showing admin features");
                    showAdminFeatures();
                }
                return;
            }

            const user = await getCurrentUser();
            console.log("Current user:", user);

            const roleEl = document.getElementById("bcUserRole");
            if (roleEl) {
                roleEl.textContent = user.role || "Resident";
                console.log("Updated role display to:", user.role);
            }

            // Show/hide admin-specific features
            if (user.role === "ADMIN") {
                console.log("User is ADMIN, showing admin features");
                showAdminFeatures();
            }
        } catch (err) {
            console.error("Failed to load current user:", err);
        }
    }

    function showAdminFeatures() {
        console.log("Showing admin features...");

        // Hide resident-specific sections for admin
        hideResidentSections();

        // Add admin navigation items to desktop sidebar
        const sidebarNav = document.getElementById("bcSidebarNav");
        if (sidebarNav) {
            const navList = sidebarNav; // The ul itself
            if (navList) {
                // Clear existing nav items first
                navList.innerHTML = '';

                // Add BHW features for admin
                const bhwFeatures = [
                    { target: "bcBHWAnnouncements", text: "Manage Announcements", icon: "bi-megaphone" },
                    { target: "bcBHWReferrals", text: "Manage Referrals", icon: "bi-clipboard2-pulse" },
                    { target: "bcBHWUsers", text: "Resident Profiles", icon: "bi-people" },
                    { target: "bcAdminPanel", text: "Admin Panel", icon: "bi-shield-check" }
                ];

                bhwFeatures.forEach(feature => {
                    const navItem = document.createElement("li");
                    navItem.className = "nav-item";
                    navItem.innerHTML = `
                        <button class="nav-link" data-target="${feature.target}">
                            <i class="bi ${feature.icon}"></i> ${feature.text}
                        </button>
                    `;
                    navList.appendChild(navItem);
                });

                console.log("Added BHW features and admin navigation to desktop sidebar");
            }
        } else {
            console.log("Desktop sidebar navigation not found");
        }

        // Add admin navigation to mobile menu
        const mobileNav = document.getElementById("bcMobileNav");
        if (mobileNav) {
            // Clear existing mobile nav items
            mobileNav.innerHTML = '';

            // Add BHW features for admin (mobile)
            const bhwFeatures = [
                { target: "bcBHWAnnouncements", text: "Manage Announcements", icon: "bi-megaphone" },
                { target: "bcBHWReferrals", text: "Manage Referrals", icon: "bi-clipboard2-pulse" },
                { target: "bcBHWUsers", text: "Resident Profiles", icon: "bi-people" },
                { target: "bcAdminPanel", text: "Admin Panel", icon: "bi-shield-check" }
            ];

            bhwFeatures.forEach(feature => {
                const navItem = document.createElement("li");
                navItem.className = "nav-item";
                navItem.innerHTML = `
                    <button class="nav-link" data-target="${feature.target}">
                        <i class="bi ${feature.icon}"></i> ${feature.text}
                    </button>
                `;
                mobileNav.appendChild(navItem);
            });

            console.log("Added BHW features and admin navigation to mobile menu");
        }

        // Create BHW and admin sections
        createBHWSections();
        createAdminPanel();

        // Show admin dashboard by default
        activateSection("bcBHWAnnouncements");
    }

    function hideResidentSections() {
        // Hide resident-specific sections
        const residentSections = ['bcDashboard', 'bcSymptom', 'bcRecords', 'bcReferrals'];
        residentSections.forEach(sectionId => {
            const section = document.getElementById(sectionId);
            if (section) {
                section.style.display = 'none';
            }
        });

        // Hide resident cards in dashboard
        const symptomCard = document.querySelector('[data-target="bcSymptom"]');
        if (symptomCard) symptomCard.closest('.bc-card').style.display = 'none';

        const referralCard = document.querySelector('[data-target="bcReferrals"]');
        if (referralCard) referralCard.closest('.bc-card').style.display = 'none';
    }

    function createBHWSections() {
        const mainContent = document.querySelector("main");
        if (!mainContent) {
            console.log("Main content area not found");
            return;
        }

        // BHW Announcements Management
        const bhwAnnouncements = document.createElement("section");
        bhwAnnouncements.id = "bcBHWAnnouncements";
        bhwAnnouncements.className = "bc-page bc-fade-slide";
        bhwAnnouncements.style.display = "none";
        bhwAnnouncements.innerHTML = `
            <div class="row g-3">
                <div class="col-12">
                    <h2>Manage Announcements</h2>
                    <p class="bc-muted">Create, edit, and manage community announcements</p>
                </div>
                <div class="col-12">
                    <div class="bc-card card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 class="mb-0">Announcement Management</h5>
                                <div>
                                    <button class="btn btn-success" onclick="showCreateAnnouncementForm()">
                                        <i class="bi bi-plus-circle"></i> Create New
                                    </button>
                                    <button class="btn btn-outline-primary" onclick="loadBHWAnnouncements()">
                                        <i class="bi bi-arrow-clockwise"></i> Refresh
                                    </button>
                                </div>
                            </div>
                            <div id="bhwAnnouncementList"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        mainContent.appendChild(bhwAnnouncements);

        // BHW Referrals Management
        const bhwReferrals = document.createElement("section");
        bhwReferrals.id = "bcBHWReferrals";
        bhwReferrals.className = "bc-page bc-fade-slide";
        bhwReferrals.style.display = "none";
        bhwReferrals.innerHTML = `
            <div class="row g-3">
                <div class="col-12">
                    <h2>Manage Referrals</h2>
                    <p class="bc-muted">View and manage patient referral slips</p>
                </div>
                <div class="col-12">
                    <div class="bc-card card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 class="mb-0">Referral Slips</h5>
                                <button class="btn btn-outline-primary" onclick="loadBHWReferrals()">
                                    <i class="bi bi-arrow-clockwise"></i> Refresh
                                </button>
                            </div>
                            <div id="bhwReferralList"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        mainContent.appendChild(bhwReferrals);

        // BHW User Profiles
        const bhwUsers = document.createElement("section");
        bhwUsers.id = "bcBHWUsers";
        bhwUsers.className = "bc-page bc-fade-slide";
        bhwUsers.style.display = "none";
        bhwUsers.innerHTML = `
            <div class="row g-3">
                <div class="col-12">
                    <h2>Resident Profiles</h2>
                    <p class="bc-muted">View and search resident health profiles</p>
                </div>
                <div class="col-12">
                    <div class="bc-card card">
                        <div class="card-body">
                            <div class="mb-3">
                                <div class="input-group">
                                    <input type="text" class="form-control" id="userSearchInput" placeholder="Search by name, username, or barangay">
                                    <button class="btn btn-primary" onclick="searchUsers()">
                                        <i class="bi bi-search"></i> Search
                                    </button>
                                </div>
                            </div>
                            <div id="bhwUserList" style="max-height: 500px; overflow-y: auto;"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        mainContent.appendChild(bhwUsers);

        console.log("Added BHW sections");

        // Load initial data
        loadBHWAnnouncements();
        loadBHWReferrals();
    }

    function createAdminPanel() {
        const mainContent = document.querySelector("main");
        if (!mainContent) return;

        const adminPanel = document.createElement("section");
        adminPanel.id = "bcAdminPanel";
        adminPanel.className = "bc-page bc-fade-slide";
        adminPanel.style.display = "none";
        adminPanel.innerHTML = `
            <div class="row g-3">
                <div class="col-12">
                    <h2>Admin Panel</h2>
                    <p class="bc-muted">System administration and user management</p>
                </div>
                <div class="col-12 col-md-6">
                    <div class="bc-card card">
                        <div class="card-body">
                            <h5 class="card-title">
                                <i class="bi bi-person-check"></i> BHW Approvals
                            </h5>
                            <p class="card-text">Review and approve BHW account applications</p>
                            <a href="/pages/admin_approval.html" class="btn btn-primary">
                                <i class="bi bi-eye"></i> Manage Approvals
                            </a>
                        </div>
                    </div>
                </div>
                <div class="col-12 col-md-6">
                    <div class="bc-card card">
                        <div class="card-body">
                            <h5 class="card-title">
                                <i class="bi bi-people"></i> User Management
                            </h5>
                            <p class="card-text">View and manage all system users</p>
                            <button class="btn btn-secondary" onclick="alert('User management coming soon!')">
                                <i class="bi bi-gear"></i> View All Users
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        mainContent.appendChild(adminPanel);
        console.log("Added admin panel section");
    }

    function addAnnouncementCreationButton() {
        const announcementSection = document.getElementById("bcAnnouncementList");
        if (announcementSection) {
            const parent = announcementSection.parentElement;
            const header = parent.querySelector("h5");
            if (header && !parent.querySelector(".btn-success")) {
                const createBtn = document.createElement("button");
                createBtn.className = "btn btn-success btn-sm ms-2";
                createBtn.innerHTML = '<i class="bi bi-plus-circle"></i> Create Announcement';
                createBtn.onclick = () => showCreateAnnouncementForm();
                header.appendChild(createBtn);
                console.log("Added create announcement button");
            }
        }
    }

    function showCreateAnnouncementForm() {
        const formHtml = `
            <div class="card mt-3">
                <div class="card-body">
                    <h5 class="card-title">Create New Announcement</h5>
                    <form id="createAnnouncementForm">
                        <div class="mb-3">
                            <label class="form-label">Title</label>
                            <input type="text" class="form-control" name="title" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Message</label>
                            <textarea class="form-control" name="body" rows="3" required></textarea>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Category</label>
                            <select class="form-select" name="category" required>
                                <option value="">Select category</option>
                                <option value="Health">Health</option>
                                <option value="Safety">Safety</option>
                                <option value="Community">Community</option>
                                <option value="Emergency">Emergency</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Barangay</label>
                            <input type="text" class="form-control" name="barangay" required>
                        </div>
                        <div class="mb-3">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" name="is_emergency">
                                <label class="form-check-label">Mark as Emergency</label>
                            </div>
                        </div>
                        <div class="d-flex gap-2">
                            <button type="submit" class="btn btn-primary">Create Announcement</button>
                            <button type="button" class="btn btn-secondary" onclick="hideCreateAnnouncementForm()">Cancel</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        // Remove existing form if any
        const existingForm = document.getElementById("createAnnouncementForm");
        if (existingForm) {
            existingForm.closest(".card").remove();
        }

        // Add new form
        const announcementSection = document.getElementById("bcAnnouncementList");
        if (announcementSection) {
            // Insert the form after the announcement list container
            announcementSection.insertAdjacentHTML("afterend", formHtml);

            // Add form submit handler
            document.getElementById("createAnnouncementForm").addEventListener("submit", async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const data = {
                    title: formData.get("title"),
                    body: formData.get("body"),
                    category: formData.get("category"),
                    barangay: formData.get("barangay"),
                    is_emergency: formData.has("is_emergency")
                };

                try {
                    await createAnnouncement(data);
                    showToast("Announcement created successfully!", "success");
                    hideCreateAnnouncementForm();
                    loadAnnouncements(); // Refresh the list
                } catch (err) {
                    showToast("Failed to create announcement: " + err.message, "danger");
                }
            });
        }
    }

    function hideCreateAnnouncementForm() {
        const form = document.getElementById("createAnnouncementForm");
        if (form) {
            form.closest(".card").remove();
        }
    }

    // BHW Functions for Admin
    async function loadBHWAnnouncements() {
        const container = document.getElementById("bhwAnnouncementList");
        if (!container) {
            console.log("bhwAnnouncementList not found");
            return;
        }

        container.innerHTML = '<p class="bc-muted"><i class="bi bi-arrow-clockwise"></i> Loading announcements...</p>';

        try {
            console.log("Loading BHW announcements...");
            const announcements = await getAnnouncements();
            console.log("Announcements loaded:", announcements);

            if (!announcements || !announcements.length) {
                container.innerHTML = `
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle"></i> No announcements found. 
                        <button class="btn btn-success btn-sm ms-2" onclick="showCreateAnnouncementForm()">
                            <i class="bi bi-plus-circle"></i> Create First Announcement
                        </button>
                    </div>
                `;
                return;
            }

            container.innerHTML = announcements.map(a => `
                <div class="bc-announcement-item mb-3">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">
                                ${a.title}
                                ${a.is_emergency ? '<span class="badge bg-danger ms-2">EMERGENCY</span>' : ''}
                            </h6>
                            <p class="bc-muted small mb-1">
                                <strong>Category:</strong> ${a.category || 'N/A'} | 
                                <strong>Barangay:</strong> ${a.barangay || 'N/A'}
                            </p>
                            <p class="mb-2">${a.body}</p>
                            <small class="bc-muted">${new Date(a.created_at).toLocaleString()}</small>
                        </div>
                        <div class="d-flex gap-1">
                            <button class="btn btn-sm btn-outline-primary" onclick="editAnnouncement(${a.id})" title="Edit">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="archiveAnnouncement(${a.id})" title="Archive">
                                <i class="bi bi-archive"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');

        } catch (err) {
            console.error("Failed to load BHW announcements:", err);
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Failed to load announcements: ${err.message}
                    <button class="btn btn-outline-primary btn-sm ms-2" onclick="loadBHWAnnouncements()">
                        <i class="bi bi-arrow-clockwise"></i> Retry
                    </button>
                </div>
            `;
        }
    }

    async function loadBHWReferrals() {
        const container = document.getElementById("bhwReferralList");
        if (!container) {
            console.log("bhwReferralList not found");
            return;
        }

        container.innerHTML = '<div class="bc-skeleton" style="height: 100px; width: 100%; margin-bottom: 15px;"></div><div class="bc-skeleton" style="height: 100px; width: 100%;"></div>';

        try {
            console.log("Loading BHW referrals...");
            const referrals = await getReferrals();
            console.log("Referrals loaded:", referrals);

            if (!referrals || !referrals.length) {
                container.innerHTML = `
                    <div class="bc-empty-state">
                        <i class="bi bi-file-medical"></i>
                        <h6>No Referrals Found</h6>
                        <p class="small mb-0">There are no referral slips recorded.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = referrals.map(r => `
                <div class="bc-announcement-item mb-3">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">Referral ${r.referral_code}</h6>
                            <p class="bc-muted small mb-1">
                                <strong>Center:</strong> ${r.referred_to_center || 'N/A'} | 
                                <strong>Status:</strong> <span class="badge bg-info">${r.status || 'N/A'}</span>
                            </p>
                            <small class="bc-muted">Generated: ${new Date(r.generated_at).toLocaleString()}</small>
                        </div>
                        <div class="d-flex gap-1">
                            <button class="btn btn-sm btn-outline-primary" onclick="updateReferralStatus(${r.id})" title="Update Status">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-primary" onclick="downloadReferral(${r.id}, '${r.referral_code}')" title="Download PDF">
                                <i class="bi bi-download"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');

        } catch (err) {
            console.error("Failed to load BHW referrals:", err);
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Failed to load referrals: ${err.message}
                    <button class="btn btn-outline-primary btn-sm ms-2" onclick="loadBHWReferrals()">
                        <i class="bi bi-arrow-clockwise"></i> Retry
                    </button>
                </div>
            `;
        }
    }

    async function searchUsers() {
        const container = document.getElementById("bhwUserList");
        const searchInput = document.getElementById("userSearchInput");
        if (!container) return;

        const searchTerm = searchInput ? searchInput.value.trim() : '';

        container.innerHTML = '<div class="bc-skeleton" style="height: 100px; width: 100%; margin-bottom: 15px;"></div><div class="bc-skeleton" style="height: 100px; width: 100%;"></div>';

        try {
            // Backend now defaults to RESIDENT-only
            const url = searchTerm
                ? `/profile/search?q=${encodeURIComponent(searchTerm)}`
                : '/profile/search';

            const residents = await apiCall(url);

            if (!residents || residents.length === 0) {
                container.innerHTML = `
                    <div class="bc-empty-state">
                        <i class="bi bi-people"></i>
                        <h6>No Residents Found</h6>
                        <p class="small mb-0">${searchTerm ? `No residents found matching "${searchTerm}".` : 'No registered residents found.'}</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-3 sticky-top bg-white pt-2 pb-2 border-bottom">
                    <h6 class="mb-0"><i class="bi bi-people"></i> ${residents.length} Registered Resident${residents.length > 1 ? 's' : ''}</h6>
                    ${searchTerm ? `<button class="btn btn-sm btn-outline-secondary" onclick="document.getElementById('userSearchInput').value=''; searchUsers();"><i class="bi bi-x"></i> Clear</button>` : ''}
                </div>
                <div class="resident-list">
                    ${residents.map(user => `
                    <div class="bc-announcement-item mb-3 p-3 border rounded">
                        <div class="row align-items-center">
                            <!-- Left side: User info -->
                            <div class="col">
                                <h6 class="mb-1 fw-bold">${user.full_name || user.username}</h6>
                                <p class="bc-muted small mb-1">
                                    <i class="bi bi-person"></i> ${user.username} | 
                                    <i class="bi bi-geo-alt"></i> ${user.barangay || 'N/A'}
                                </p>
                                <p class="bc-muted small mb-0">
                                    <i class="bi bi-telephone"></i> ${user.contact_number || 'N/A'} | 
                                    <i class="bi bi-envelope"></i> ${user.email}
                                </p>
                            </div>
                            <!-- Right side: Action buttons -->
                            <div class="col-auto ps-3">
                                <div class="d-flex flex-column gap-2">
                                    <button class="btn btn-primary btn-sm" onclick="viewResidentProfile(${user.id}, '${user.full_name || user.username}')" title="View Health Profile">
                                        <i class="bi bi-eye"></i> Show Profile
                                    </button>
                                    <button class="btn btn-success btn-sm" onclick="downloadResidentProfile(${user.id}, '${user.full_name || user.username}')" title="Download Health Profile PDF">
                                        <i class="bi bi-download"></i> Download
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('')}
                </div>`;

        } catch (err) {
            console.error("Failed to load residents:", err);
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Failed to load residents: ${err.message}
                    <button class="btn btn-outline-primary btn-sm ms-2" onclick="searchUsers()">
                        <i class="bi bi-arrow-clockwise"></i> Retry
                    </button>
                </div>
            `;
        }
    }

    // View resident profile (read-only for BHW)
    async function downloadResidentProfile(userId, userName) {
        try {
            const profile = await apiCall(`/profile/${userId}`);

            // Create a clean printable HTML
            const printHtml = `
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Health Profile - ${userName}</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; color: #333; }
                        .header { text-align: center; border-bottom: 3px solid #0d6efd; padding-bottom: 20px; margin-bottom: 30px; }
                        .header h1 { color: #0d6efd; margin: 0; }
                        .header p { margin: 5px 0; color: #666; }
                        .section { margin-bottom: 25px; }
                        .section-title { color: #0d6efd; font-size: 16px; font-weight: bold; border-bottom: 2px solid #0d6efd; padding-bottom: 5px; margin-bottom: 15px; }
                        .row { display: flex; flex-wrap: wrap; margin-bottom: 8px; }
                        .col-6 { width: 50%; padding-right: 20px; box-sizing: border-box; }
                        .col-12 { width: 100%; }
                        .label { font-weight: bold; color: #555; }
                        .value { color: #333; }
                        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; font-size: 12px; color: #999; }
                        @media print { .no-print { display: none; } }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>BARANGAY HEALTH PROFILE</h1>
                        <p>BAYANCARE Digital Health System</p>
                        <p>Generated on: ${new Date().toLocaleDateString()}</p>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">I. PERSONAL IDENTIFICATION</div>
                        <div class="row">
                            <div class="col-6"><span class="label">Name:</span> <span class="value">${profile.last_name || ''}${profile.last_name && profile.first_name ? ', ' : ''}${profile.first_name || ''}${profile.middle_name ? ' ' + profile.middle_name : ''}</span></div>
                            <div class="col-6"><span class="label">Age:</span> <span class="value">${profile.age ?? 'N/A'}</span></div>
                        </div>
                        <div class="row">
                            <div class="col-6"><span class="label">Sex:</span> <span class="value">${profile.sex || 'N/A'}</span></div>
                            <div class="col-6"><span class="label">Date of Birth:</span> <span class="value">${profile.date_of_birth ? new Date(profile.date_of_birth).toLocaleDateString() : 'N/A'}</span></div>
                        </div>
                        <div class="row">
                            <div class="col-6"><span class="label">Civil Status:</span> <span class="value">${profile.civil_status || 'N/A'}</span></div>
                            <div class="col-6"><span class="label">PhilHealth ID:</span> <span class="value">${profile.philhealth_id || 'N/A'}</span></div>
                        </div>
                        <div class="row">
                            <div class="col-12"><span class="label">Address:</span> <span class="value">${profile.address || 'N/A'}</span></div>
                        </div>
                        <div class="row">
                            <div class="col-12"><span class="label">Contact Number:</span> <span class="value">${profile.contact_number || 'N/A'}</span></div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">II. MEDICAL HISTORY & SOCIAL DETERMINANTS</div>
                        <div class="row">
                            <div class="col-6"><span class="label">Blood Type:</span> <span class="value">${profile.blood_type || 'N/A'}</span></div>
                            <div class="col-6"><span class="label">PWD ID:</span> <span class="value">${profile.pwd_id || 'N/A'}</span></div>
                        </div>
                        <div class="row">
                            <div class="col-12"><span class="label">Known Allergies:</span> <span class="value">${profile.allergies || 'None'}</span></div>
                        </div>
                        <div class="row">
                            <div class="col-12"><span class="label">Chronic Conditions:</span> <span class="value">${profile.chronic_conditions || 'None'}</span></div>
                        </div>
                        <div class="row">
                            <div class="col-12"><span class="label">Current Medications:</span> <span class="value">${profile.current_medications || 'None'}</span></div>
                        </div>
                        <div class="row">
                            <div class="col-12"><span class="label">Lifestyle (Smoker/Alcohol):</span> <span class="value">${profile.lifestyle || 'N/A'}</span></div>
                        </div>
                        <div class="row">
                            <div class="col-12"><span class="label">Household Details:</span> <span class="value">${profile.household_details || 'N/A'}</span></div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">III. PUBLIC HEALTH PROGRAM STATUS</div>
                        <div class="row">
                            <div class="col-12"><span class="label">COVID-19 Vaccination:</span> <span class="value">${profile.covid_vaccination || 'N/A'}</span></div>
                        </div>
                        <div class="row">
                            <div class="col-12"><span class="label">Other Immunizations:</span> <span class="value">${profile.other_immunizations || 'N/A'}</span></div>
                        </div>
                        <div class="row">
                            <div class="col-12"><span class="label">Maternal & Child Health Notes:</span> <span class="value">${profile.maternal_child_health || 'N/A'}</span></div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">IV. EMERGENCY CONTACT INFO & CERTIFICATION</div>
                        <div class="row">
                            <div class="col-12"><span class="label">Emergency Contact Person:</span> <span class="value">${profile.emergency_contact_person || 'N/A'}</span></div>
                        </div>
                        <div class="row">
                            <div class="col-6"><span class="label">Relationship:</span> <span class="value">${profile.emergency_contact_relationship || 'N/A'}</span></div>
                            <div class="col-6"><span class="label">Contact Number:</span> <span class="value">${profile.emergency_contact_number || 'N/A'}</span></div>
                        </div>
                        <div class="row">
                            <div class="col-6"><span class="label">Processed By (BHW):</span> <span class="value">${profile.processed_by_bhw || 'N/A'}</span></div>
                            <div class="col-6"><span class="label">Date:</span> <span class="value">${profile.processed_date ? new Date(profile.processed_date).toLocaleDateString() : 'N/A'}</span></div>
                        </div>
                    </div>
                    
                    <div class="footer no-print">
                        <p>This document was generated by BAYANCARE - Barangay Health Advisory System</p>
                        <button onclick="window.print()" style="padding: 10px 20px; background: #0d6efd; color: white; border: none; border-radius: 5px; cursor: pointer;">Print / Save as PDF</button>
                    </div>
                </body>
                </html>
            `;

            // Open in new window
            const printWindow = window.open('', '_blank');
            printWindow.document.write(printHtml);
            printWindow.document.close();

            showToast("Health profile opened for download", "success");

        } catch (err) {
            console.error("Failed to download profile:", err);
            showToast("Failed to download profile: " + err.message, "danger");
        }
    }

    // View resident profile (read-only for BHW)
    async function viewResidentProfile(userId, userName) {
        try {
            const profile = await apiCall(`/profile/${userId}`);

            const modalHtml = `
                <div class="modal fade" id="viewResidentProfileModal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-lg modal-dialog-scrollable">
                        <div class="modal-content">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title">
                                    <i class="bi bi-person-vcard"></i> ${userName}'s Health Profile
                                </h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="health-profile">
                                    <!-- I. PERSONAL IDENTIFICATION -->
                                    <div class="profile-section mb-4">
                                        <h6 class="section-title text-primary border-bottom pb-1 mb-2">
                                            <i class="bi bi-person-vcard"></i> I. PERSONAL IDENTIFICATION
                                        </h6>
                                        <div class="row g-2 small">
                                            <div class="col-12 col-md-6"><strong>Name:</strong> ${profile.last_name || ''}${profile.last_name && profile.first_name ? ', ' : ''}${profile.first_name || ''}${profile.middle_name ? ' ' + profile.middle_name : ''}</div>
                                            <div class="col-6 col-md-3"><strong>Age:</strong> ${profile.age ?? 'N/A'}</div>
                                            <div class="col-6 col-md-3"><strong>Sex:</strong> ${profile.sex || 'N/A'}</div>
                                            <div class="col-6 col-md-4"><strong>DOB:</strong> ${profile.date_of_birth ? new Date(profile.date_of_birth).toLocaleDateString() : 'N/A'}</div>
                                            <div class="col-6 col-md-4"><strong>Civil Status:</strong> ${profile.civil_status || 'N/A'}</div>
                                            <div class="col-12"><strong>Address:</strong> ${profile.address || 'N/A'}</div>
                                            <div class="col-6 col-md-6"><strong>Contact:</strong> ${profile.contact_number || 'N/A'}</div>
                                            <div class="col-6 col-md-6"><strong>PhilHealth ID:</strong> ${profile.philhealth_id || 'N/A'}</div>
                                        </div>
                                    </div>
                                    
                                    <!-- II. MEDICAL HISTORY & SOCIAL DETERMINANTS -->
                                    <div class="profile-section mb-4">
                                        <h6 class="section-title text-primary border-bottom pb-1 mb-2">
                                            <i class="bi bi-heart-pulse"></i> II. MEDICAL HISTORY & SOCIAL DETERMINANTS
                                        </h6>
                                        <div class="row g-2 small">
                                            <div class="col-6 col-md-4"><strong>Blood Type:</strong> ${profile.blood_type || 'N/A'}</div>
                                            <div class="col-6 col-md-8"><strong>PWD ID:</strong> ${profile.pwd_id || 'N/A'}</div>
                                            <div class="col-12"><strong>Known Allergies:</strong> ${profile.allergies || 'None'}</div>
                                            <div class="col-12"><strong>Chronic Conditions:</strong> ${profile.chronic_conditions || 'None'}</div>
                                            <div class="col-12"><strong>Current Medications:</strong> ${profile.current_medications || 'None'}</div>
                                            <div class="col-12"><strong>Lifestyle (Smoker/Alcohol):</strong> ${profile.lifestyle || 'N/A'}</div>
                                            <div class="col-12"><strong>Household Details:</strong> ${profile.household_details || 'N/A'}</div>
                                        </div>
                                    </div>
                                    
                                    <!-- III. PUBLIC HEALTH PROGRAM STATUS -->
                                    <div class="profile-section mb-4">
                                        <h6 class="section-title text-primary border-bottom pb-1 mb-2">
                                            <i class="bi bi-shield-check"></i> III. PUBLIC HEALTH PROGRAM STATUS
                                        </h6>
                                        <div class="row g-2 small">
                                            <div class="col-12"><strong>COVID-19 Vaccination:</strong> ${profile.covid_vaccination || 'N/A'}</div>
                                            <div class="col-12"><strong>Other Immunizations:</strong> ${profile.other_immunizations || 'N/A'}</div>
                                            <div class="col-12"><strong>Maternal & Child Health Notes:</strong> ${profile.maternal_child_health || 'N/A'}</div>
                                        </div>
                                    </div>
                                    
                                    <!-- IV. EMERGENCY CONTACT INFO & CERTIFICATION -->
                                    <div class="profile-section mb-4">
                                        <h6 class="section-title text-primary border-bottom pb-1 mb-2">
                                            <i class="bi bi-telephone-emergency"></i> IV. EMERGENCY CONTACT INFO & CERTIFICATION
                                        </h6>
                                        <div class="row g-2 small">
                                            <div class="col-12 col-md-6"><strong>Emergency Contact:</strong> ${profile.emergency_contact_person || 'N/A'}</div>
                                            <div class="col-6 col-md-3"><strong>Relationship:</strong> ${profile.emergency_contact_relationship || 'N/A'}</div>
                                            <div class="col-6 col-md-3"><strong>Number:</strong> ${profile.emergency_contact_number || 'N/A'}</div>
                                            <div class="col-6 col-md-6"><strong>Processed By (BHW):</strong> ${profile.processed_by_bhw || 'N/A'}</div>
                                            <div class="col-6 col-md-6"><strong>Date:</strong> ${profile.processed_date ? new Date(profile.processed_date).toLocaleDateString() : 'N/A'}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button class="btn btn-sm btn-outline-primary" onclick="viewResidentProfile(${userId}, '${userName}')" data-bs-dismiss="modal">
                                    <i class="bi bi-pencil"></i> Edit Profile
                                </button>
                                <button class="btn btn-success" onclick="downloadResidentProfile(${userId}, '${userName}')">
                                    <i class="bi bi-download"></i> Download PDF
                                </button>
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Remove existing modal
            const existingModal = document.getElementById("viewResidentProfileModal");
            if (existingModal) {
                existingModal.remove();
            }

            // Add modal to body
            document.body.insertAdjacentHTML("beforeend", modalHtml);

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById("viewResidentProfileModal"));
            modal.show();

        } catch (err) {
            console.error("Failed to load resident profile:", err);
            showToast("Failed to load resident profile: " + err.message, "danger");
        }
    }

    // Edit resident profile (BHW can edit)
    async function editResidentProfile(userId, userName) {
        try {
            const profile = await apiCall(`/profile/${userId}`);

            const modalHtml = `
                <div class="modal fade" id="editResidentProfileModal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-lg modal-dialog-scrollable">
                        <div class="modal-content">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title">
                                    <i class="bi bi-pencil-square"></i> Edit ${userName}'s Health Profile
                                </h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <form id="bhwEditProfileForm">
                                    <!-- I. PERSONAL IDENTIFICATION -->
                                    <h6 class="mb-2 text-primary border-bottom pb-1"><i class="bi bi-person-vcard"></i> I. PERSONAL IDENTIFICATION</h6>
                                    <div class="row g-2 mb-3">
                                        <div class="col-12 col-md-4">
                                            <label class="form-label small">Last Name</label>
                                            <input type="text" class="form-control form-control-sm" name="last_name" value="${profile.last_name || ''}">
                                        </div>
                                        <div class="col-12 col-md-4">
                                            <label class="form-label small">First Name</label>
                                            <input type="text" class="form-control form-control-sm" name="first_name" value="${profile.first_name || ''}">
                                        </div>
                                        <div class="col-12 col-md-4">
                                            <label class="form-label small">Middle Name</label>
                                            <input type="text" class="form-control form-control-sm" name="middle_name" value="${profile.middle_name || ''}">
                                        </div>
                                        <div class="col-6 col-md-4">
                                            <label class="form-label small">Date of Birth</label>
                                            <input type="date" class="form-control form-control-sm" name="date_of_birth" value="${profile.date_of_birth || ''}">
                                        </div>
                                        <div class="col-6 col-md-2">
                                            <label class="form-label small">Age</label>
                                            <input type="number" class="form-control form-control-sm" name="age" value="${profile.age || ''}">
                                        </div>
                                        <div class="col-6 col-md-3">
                                            <label class="form-label small">Sex</label>
                                            <select class="form-select form-select-sm" name="sex">
                                                <option value="">Select</option>
                                                <option value="Male" ${profile.sex === 'Male' ? 'selected' : ''}>Male</option>
                                                <option value="Female" ${profile.sex === 'Female' ? 'selected' : ''}>Female</option>
                                                <option value="Other" ${profile.sex === 'Other' ? 'selected' : ''}>Other</option>
                                            </select>
                                        </div>
                                        <div class="col-6 col-md-3">
                                            <label class="form-label small">Civil Status</label>
                                            <select class="form-select form-select-sm" name="civil_status">
                                                <option value="">Select</option>
                                                <option value="Single" ${profile.civil_status === 'Single' ? 'selected' : ''}>Single</option>
                                                <option value="Married" ${profile.civil_status === 'Married' ? 'selected' : ''}>Married</option>
                                                <option value="Widowed" ${profile.civil_status === 'Widowed' ? 'selected' : ''}>Widowed</option>
                                                <option value="Separated" ${profile.civil_status === 'Separated' ? 'selected' : ''}>Separated</option>
                                            </select>
                                        </div>
                                        <div class="col-12">
                                            <label class="form-label small">Full Address</label>
                                            <textarea class="form-control form-control-sm" name="address" rows="2">${profile.address || ''}</textarea>
                                        </div>
                                        <div class="col-6 col-md-6">
                                            <label class="form-label small">Contact Number</label>
                                            <input type="text" class="form-control form-control-sm" name="contact_number" value="${profile.contact_number || ''}">
                                        </div>
                                        <div class="col-6 col-md-6">
                                            <label class="form-label small">PhilHealth ID No.</label>
                                            <input type="text" class="form-control form-control-sm" name="philhealth_id" value="${profile.philhealth_id || ''}">
                                        </div>
                                    </div>

                                    <!-- II. MEDICAL HISTORY & SOCIAL DETERMINANTS -->
                                    <h6 class="mb-2 text-primary border-bottom pb-1"><i class="bi bi-heart-pulse"></i> II. MEDICAL HISTORY & SOCIAL DETERMINANTS</h6>
                                    <div class="row g-2 mb-3">
                                        <div class="col-6 col-md-3">
                                            <label class="form-label small">Blood Type</label>
                                            <select class="form-select form-select-sm" name="blood_type">
                                                <option value="">Select</option>
                                                <option value="A+" ${profile.blood_type === 'A+' ? 'selected' : ''}>A+</option>
                                                <option value="A-" ${profile.blood_type === 'A-' ? 'selected' : ''}>A-</option>
                                                <option value="B+" ${profile.blood_type === 'B+' ? 'selected' : ''}>B+</option>
                                                <option value="B-" ${profile.blood_type === 'B-' ? 'selected' : ''}>B-</option>
                                                <option value="AB+" ${profile.blood_type === 'AB+' ? 'selected' : ''}>AB+</option>
                                                <option value="AB-" ${profile.blood_type === 'AB-' ? 'selected' : ''}>AB-</option>
                                                <option value="O+" ${profile.blood_type === 'O+' ? 'selected' : ''}>O+</option>
                                                <option value="O-" ${profile.blood_type === 'O-' ? 'selected' : ''}>O-</option>
                                            </select>
                                        </div>
                                        <div class="col-6 col-md-5">
                                            <label class="form-label small">PWD ID No. (if any)</label>
                                            <input type="text" class="form-control form-control-sm" name="pwd_id" value="${profile.pwd_id || ''}">
                                        </div>
                                        <div class="col-12">
                                            <label class="form-label small">Known Allergies</label>
                                            <textarea class="form-control form-control-sm" name="allergies" rows="2">${profile.allergies || ''}</textarea>
                                        </div>
                                        <div class="col-12">
                                            <label class="form-label small">Chronic Conditions</label>
                                            <textarea class="form-control form-control-sm" name="chronic_conditions" rows="2">${profile.chronic_conditions || ''}</textarea>
                                        </div>
                                        <div class="col-12">
                                            <label class="form-label small">Current Medications</label>
                                            <textarea class="form-control form-control-sm" name="current_medications" rows="2">${profile.current_medications || ''}</textarea>
                                        </div>
                                        <div class="col-12">
                                            <label class="form-label small">Lifestyle (Smoker/Alcohol)</label>
                                            <input type="text" class="form-control form-control-sm" name="lifestyle" value="${profile.lifestyle || ''}">
                                        </div>
                                        <div class="col-12">
                                            <label class="form-label small">Household Details</label>
                                            <textarea class="form-control form-control-sm" name="household_details" rows="2">${profile.household_details || ''}</textarea>
                                        </div>
                                    </div>

                                    <!-- III. PUBLIC HEALTH PROGRAM STATUS -->
                                    <h6 class="mb-2 text-primary border-bottom pb-1"><i class="bi bi-shield-check"></i> III. PUBLIC HEALTH PROGRAM STATUS</h6>
                                    <div class="row g-2 mb-3">
                                        <div class="col-12">
                                            <label class="form-label small">COVID-19 Vaccination Status</label>
                                            <input type="text" class="form-control form-control-sm" name="covid_vaccination" value="${profile.covid_vaccination || ''}">
                                        </div>
                                        <div class="col-12">
                                            <label class="form-label small">Other Immunizations</label>
                                            <input type="text" class="form-control form-control-sm" name="other_immunizations" value="${profile.other_immunizations || ''}">
                                        </div>
                                        <div class="col-12">
                                            <label class="form-label small">Maternal & Child Health Notes</label>
                                            <textarea class="form-control form-control-sm" name="maternal_child_health" rows="2">${profile.maternal_child_health || ''}</textarea>
                                        </div>
                                    </div>

                                    <!-- IV. EMERGENCY CONTACT INFO & CERTIFICATION -->
                                    <h6 class="mb-2 text-primary border-bottom pb-1"><i class="bi bi-telephone-emergency"></i> IV. EMERGENCY CONTACT INFO & CERTIFICATION</h6>
                                    <div class="row g-2 mb-3">
                                        <div class="col-12 col-md-6">
                                            <label class="form-label small">Emergency Contact Person</label>
                                            <input type="text" class="form-control form-control-sm" name="emergency_contact_person" value="${profile.emergency_contact_person || ''}">
                                        </div>
                                        <div class="col-6 col-md-3">
                                            <label class="form-label small">Relationship</label>
                                            <input type="text" class="form-control form-control-sm" name="emergency_contact_relationship" value="${profile.emergency_contact_relationship || ''}">
                                        </div>
                                        <div class="col-6 col-md-3">
                                            <label class="form-label small">Contact Number</label>
                                            <input type="text" class="form-control form-control-sm" name="emergency_contact_number" value="${profile.emergency_contact_number || ''}">
                                        </div>
                                        <div class="col-12 col-md-6">
                                            <label class="form-label small">Processed By (BHW)</label>
                                            <input type="text" class="form-control form-control-sm" name="processed_by_bhw" value="${profile.processed_by_bhw || ''}">
                                        </div>
                                        <div class="col-12 col-md-6">
                                            <label class="form-label small">Processing Date</label>
                                            <input type="date" class="form-control form-control-sm" name="processed_date" value="${profile.processed_date || ''}">
                                        </div>
                                    </div>
                                </form>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-success" id="bhwSaveProfileBtn">
                                    <i class="bi bi-check-circle"></i> Save Changes
                                </button>
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Remove existing modal
            const existingModal = document.getElementById("editResidentProfileModal");
            if (existingModal) {
                existingModal.remove();
            }

            // Add modal to body
            document.body.insertAdjacentHTML("beforeend", modalHtml);

            // Setup save handler
            document.getElementById("bhwSaveProfileBtn").addEventListener("click", async () => {
                const form = document.getElementById("bhwEditProfileForm");
                const formData = new FormData(form);

                const data = {
                    // I. PERSONAL IDENTIFICATION
                    full_name: formData.get("full_name") || null,
                    last_name: formData.get("last_name") || null,
                    first_name: formData.get("first_name") || null,
                    middle_name: formData.get("middle_name") || null,
                    date_of_birth: formData.get("date_of_birth") || null,
                    age: formData.get("age") ? parseInt(formData.get("age")) : null,
                    sex: formData.get("sex") || null,
                    civil_status: formData.get("civil_status") || null,
                    address: formData.get("address") || null,
                    contact_number: formData.get("contact_number") || null,
                    philhealth_id: formData.get("philhealth_id") || null,
                    // II. MEDICAL HISTORY
                    blood_type: formData.get("blood_type") || null,
                    pwd_id: formData.get("pwd_id") || null,
                    allergies: formData.get("allergies") || null,
                    chronic_conditions: formData.get("chronic_conditions") || null,
                    current_medications: formData.get("current_medications") || null,
                    lifestyle: formData.get("lifestyle") || null,
                    household_details: formData.get("household_details") || null,
                    // III. PUBLIC HEALTH PROGRAM
                    covid_vaccination: formData.get("covid_vaccination") || null,
                    other_immunizations: formData.get("other_immunizations") || null,
                    maternal_child_health: formData.get("maternal_child_health") || null,
                    // IV. EMERGENCY CONTACT
                    emergency_contact_person: formData.get("emergency_contact_person") || null,
                    emergency_contact_relationship: formData.get("emergency_contact_relationship") || null,
                    emergency_contact_number: formData.get("emergency_contact_number") || null,
                    processed_by_bhw: formData.get("processed_by_bhw") || null,
                    processed_date: formData.get("processed_date") || null
                };

                try {
                    await apiCall(`/profile/${userId}`, {
                        method: "PUT",
                        body: JSON.stringify(data)
                    });
                    showToast("Health profile updated successfully!", "success");

                    // Close modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById("editResidentProfileModal"));
                    modal.hide();

                    // Refresh user list
                    searchUsers();
                } catch (err) {
                    console.error("Failed to update profile:", err);
                    showToast("Failed to update profile: " + err.message, "danger");
                }
            });

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById("editResidentProfileModal"));
            modal.show();

        } catch (err) {
            console.error("Failed to load resident profile for editing:", err);
            showToast("Failed to load resident profile: " + err.message, "danger");
        }
    }

    // Placeholder functions for BHW features
    function editAnnouncement(id) {
        showToast("Edit announcement functionality coming soon!", "info");
    }

    async function archiveAnnouncement(id) {
        if (!confirm("Archive this announcement?")) return;

        try {
            await apiCall(`/announcements/${id}`, { method: 'DELETE' });
            showToast("Announcement archived successfully!", "success");
            loadBHWAnnouncements();
        } catch (err) {
            showToast("Failed to archive announcement: " + err.message, "danger");
        }
    }

    function updateReferralStatus(id) {
        showToast("Update referral status functionality coming soon!", "info");
    }

    function downloadReferral(id, code) {
        window.open(`/api/referrals/${id}/download`, '_blank');
    }

    // View referral slip for residents - Medical Referral Form format
    async function viewReferralSlip(id, code) {
        try {
            // Fetch referral details
            const response = await apiCall(`/referrals/${id}`);
            if (!response) {
                showToast("Referral not found", "danger");
                return;
            }

            // Check if referral is expired
            const now = new Date();
            const expiresAt = response.expires_at ? new Date(response.expires_at) : null;
            const isExpired = expiresAt && now > expiresAt;
            const daysLeft = expiresAt ? Math.ceil((expiresAt - now) / (1000 * 60 * 60 * 24)) : null;

            // Fetch user profile for additional details
            let userProfile = {};
            try {
                userProfile = await getMyProfile();
            } catch (e) {
                console.log("Could not load profile", e);
            }

            // Build expiration badge
            let expirationBadge = '';
            if (isExpired) {
                expirationBadge = `<span class="badge bg-danger fs-6"><i class="bi bi-exclamation-triangle"></i> EXPIRED - Cannot Download</span>`;
            } else if (daysLeft !== null && daysLeft <= 2) {
                expirationBadge = `<span class="badge bg-warning text-dark fs-6"><i class="bi bi-clock"></i> Expires in ${daysLeft} day${daysLeft > 1 ? 's' : ''}</span>`;
            } else if (expiresAt) {
                expirationBadge = `<span class="badge bg-success fs-6"><i class="bi bi-calendar-check"></i> Valid until ${expiresAt.toLocaleDateString()}</span>`;
            }

            const modalHtml = `
                <div class="modal fade" id="referralViewModal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title">
                                    <i class="bi bi-hospital"></i> REFERRAL SLIP
                                </h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body p-4">
                                <!-- Expiration Warning -->
                                ${expirationBadge ? `<div class="text-center mb-3">${expirationBadge}</div>` : ''}
                                
                                ${isExpired ? `
                                    <div class="alert alert-danger">
                                        <i class="bi bi-exclamation-triangle-fill"></i> <strong>This referral has expired.</strong><br>
                                        Please request a new consultation if you still need medical attention.
                                    </div>
                                ` : ''}
                                
                                <!-- Reference Number -->
                                <div class="border border-dark p-2 mb-3">
                                    <div class="row">
                                        <div class="col-12">
                                            <strong>Reference Number:</strong> ${response.referral_code || code}
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Referring Facility -->
                                <div class="border border-dark p-2 mb-3">
                                    <div class="row mb-2">
                                        <div class="col-12">
                                            <strong>Name of Referring Facility:</strong> ${response.barangay || 'Barangay Health Center'}
                                        </div>
                                    </div>
                                    <div class="row">
                                        <div class="col-8">
                                            <strong>Address:</strong> ${response.barangay || 'N/A'}, Polomolok, South Cotabato
                                        </div>
                                        <div class="col-4 text-end">
                                            <strong>Tel No./Cp No.:</strong> ${userProfile.contact_number || 'N/A'}
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Service Provider -->
                                <div class="border border-dark p-2 mb-3">
                                    <div class="row">
                                        <div class="col-8">
                                            <strong>Name/Position of Service Provider Referring:</strong> ${response.created_by_name || response.generated_by_name || 'BHW/Barangay Health Worker'}
                                        </div>
                                        <div class="col-4 text-end">
                                            <strong>Date of Referral:</strong> ${response.generated_at ? new Date(response.generated_at).toLocaleDateString() : new Date().toLocaleDateString()}
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Referred Facility -->
                                <div class="border border-dark p-2 mb-3">
                                    <div class="row">
                                        <div class="col-12">
                                            <strong>Name of the facility to which the client is being referred:</strong> ${response.referred_to_center || 'Barangay Health Center'}
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Client Information -->
                                <div class="border border-dark p-2 mb-3">
                                    <div class="row mb-2">
                                        <div class="col-9">
                                            <strong>Name of client:</strong> ${userProfile.last_name || ''}${userProfile.last_name && userProfile.first_name ? ', ' : ''}${userProfile.first_name || ''}${userProfile.middle_name ? ' ' + userProfile.middle_name : ''}
                                        </div>
                                        <div class="col-3 text-end">
                                            <strong>Age:</strong> ${userProfile.age || 'N/A'}
                                        </div>
                                    </div>
                                    <div class="row">
                                        <div class="col-12">
                                            <strong>Address:</strong> ${userProfile.barangay || 'N/A'}, Polomolok, South Cotabato
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Reason for Referral -->
                                <div class="border border-dark p-2 mb-3">
                                    <div class="row">
                                        <div class="col-12">
                                            <strong>Reason for Referral:</strong>
                                            <p class="mb-0 mt-1">${response.symptoms ? JSON.parse(response.symptoms).join(', ') : 'High-risk symptoms identified through BAYANCARE symptom assessment requiring immediate medical evaluation and treatment.'}</p>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Brief History -->
                                <div class="border border-dark p-2 mb-3" style="min-height: 100px;">
                                    <div class="row">
                                        <div class="col-12">
                                            <strong>Brief History (include pertinent PE and laboratory findings and actions taken, if any):</strong>
                                            <p class="mb-0 mt-1">${response.brief_history || 'Patient presented with symptoms assessed through the BAYANCARE digital health system. Risk classification: HIGH. Immediate referral recommended for further evaluation and management.'}</p>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Clinical Impression -->
                                <div class="border border-dark p-2 mb-3">
                                    <div class="row">
                                        <div class="col-12">
                                            <strong>Clinical Impression:</strong>
                                            <p class="mb-0 mt-1">${response.clinical_impression || 'High-risk condition requiring immediate medical attention and intervention.'}</p>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Signature Section -->
                                <div class="border border-dark p-2 mb-3">
                                    <div class="row mb-4">
                                        <div class="col-12">
                                            <strong>Signature of Person Referring:</strong>
                                            <div style="height: 40px; border-bottom: 1px solid #000; margin-top: 10px;"></div>
                                        </div>
                                    </div>
                                    <div class="row">
                                        <div class="col-12">
                                            <strong>Signature over printed name of client/guardian:</strong>
                                            <div style="height: 40px; border-bottom: 1px solid #000; margin-top: 10px;"></div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Referral Return Slip -->
                                <div class="border border-dark p-2 mb-3">
                                    <div class="row">
                                        <div class="col-12 text-center fw-bold text-uppercase mb-2">
                                            REFERRAL RETURN SLIP
                                        </div>
                                    </div>
                                    <div class="row">
                                        <div class="col-12 small">
                                            <em>(Please cut and instruct patient/guardian to deliver back to referring facility)</em>
                                        </div>
                                    </div>
                                    <div class="row mt-2">
                                        <div class="col-6">
                                            <strong>Date Seen:</strong> _______________
                                        </div>
                                        <div class="col-6">
                                            <strong>Status:</strong> <span class="badge bg-${response.status === 'PENDING' ? 'warning' : response.status === 'ATTENDED' ? 'success' : response.status === 'EXPIRED' ? 'danger' : 'secondary'}">${response.status || 'PENDING'}</span>
                                        </div>
                                    </div>
                                </div>
                                
                                <hr>
                                <div class="d-grid gap-2">
                                    ${!isExpired ? `
                                        <a href="/api/referrals/${id}/download" target="_blank" class="btn btn-primary">
                                            <i class="bi bi-download"></i> Download Referral PDF
                                        </a>
                                    ` : `
                                        <button class="btn btn-secondary" disabled>
                                            <i class="bi bi-lock"></i> Referral Expired - Cannot Download
                                        </button>
                                    `}
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                    <i class="bi bi-arrow-left"></i> Back
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Remove existing modal
            const existingModal = document.getElementById("referralViewModal");
            if (existingModal) {
                existingModal.remove();
            }

            // Add modal to body
            document.body.insertAdjacentHTML("beforeend", modalHtml);

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById("referralViewModal"));
            modal.show();

        } catch (err) {
            console.error("Failed to load referral:", err);
            showToast("Failed to load referral details", "danger");
        }
    }

    // Follow-up refresh button
    const refreshFollowUpsBtn = document.getElementById("bcRefreshFollowUps");
    if (refreshFollowUpsBtn) {
        refreshFollowUpsBtn.addEventListener("click", loadFollowUpNotifications);
    }

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

                    // Store check-in status in localStorage
                    const checkInKey = `checkin_${assessmentId}`;
                    let checkInStatus = response;

                    // If improved, mark as completed
                    if (response === 'IMPROVED') {
                        checkInStatus = 'COMPLETED';
                    }

                    localStorage.setItem(checkInKey, JSON.stringify({
                        status: checkInStatus,
                        timestamp: new Date().toISOString(),
                        notes: notes
                    }));

                    if (result.referral_code) {
                        showToast(`Response recorded. Auto-referral generated: ${result.referral_code}`, "success");
                    } else {
                        showToast("Response recorded successfully", "success");
                    }

                    // Close modal and refresh history to show updated status
                    const modal = bootstrap.Modal.getInstance(document.getElementById("followUpResponseModal"));
                    modal.hide();
                    loadHistory(); // Refresh to show updated button status
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

    // Delete assessment handler (event delegation)
    document.body.addEventListener("click", async (e) => {
        const deleteBtn = e.target.closest('button[data-action="delete-assessment"]');
        const reviewBtn = e.target.closest('button[data-action="review-assessment"]');
        const followUpBtn = e.target.closest('button[data-action="follow-up-response"]');

        if (deleteBtn) {
            e.preventDefault();
            e.stopPropagation();
            const assessmentId = Number(deleteBtn.dataset.id);
            console.log("Delete button clicked for assessment ID:", assessmentId);
            if (!assessmentId) {
                showToast("Invalid assessment ID", "danger");
                return;
            }
            const ok = confirm("Delete this assessment from your history?");
            if (!ok) return;
            try {
                console.log("Calling deleteAssessment for ID:", assessmentId);
                await deleteAssessment(assessmentId);
                showToast("Assessment deleted.", "success");
                loadHistory();
            } catch (err) {
                console.error("Delete failed:", err);
                showToast(err.message || "Failed to delete assessment.", "danger");
            }
            return;
        }

        if (reviewBtn) {
            const assessmentId = Number(reviewBtn.dataset.id);
            if (!assessmentId) return;
            showAssessmentReview(assessmentId);
            return;
        }

        if (followUpBtn) {
            const assessmentId = Number(followUpBtn.dataset.id);
            if (!assessmentId) return;
            showFollowUpResponseModal(assessmentId);
            return;
        }
    });

    // Show assessment review modal
    async function showAssessmentReview(assessmentId) {
        try {
            // Get assessment details from history
            const items = await getMyAssessmentHistory();
            const assessment = items.find(a => a.id === assessmentId);

            if (!assessment) {
                showToast("Assessment not found.", "danger");
                return;
            }

            // Prepare data in the same format as renderAssessmentResult expects
            const assessmentData = {
                id: assessment.id,
                risk_level: assessment.risk_level,
                confidence_score: assessment.confidence_score,
                predicted_condition: assessment.predicted_condition,
                summary: assessment.assessment_summary,
                recommendations: assessment.recommendations,
                home_care_plan: assessment.home_care_plan,
                referral_generated: !!assessment.referral_id,
                referral_id: assessment.referral_id,
                referral_code: assessment.referral_code,
                created_at: assessment.created_at,
                symptoms: assessment.symptoms
            };

            const risk = (assessment.risk_level || "").toUpperCase();
            const confidence = assessment.confidence_score != null
                ? Math.round(assessment.confidence_score * 100)
                : null;

            const modalHtml = `
                <div class="modal fade" id="assessmentReviewModal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Assessment #${assessment.id} Review</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <!-- Same format as bcAssessmentResult -->
                                <div class="d-flex align-items-center mb-2">
                                    <span class="bc-risk-badge ${risk === 'LOW' ? 'bc-risk-low' : risk === 'MODERATE' ? 'bc-risk-moderate' : 'bc-risk-high'}">${risk || "UNKNOWN"}</span>
                                    <small class="bc-muted ms-2">Confidence: ${confidence != null ? `${confidence}%` : "–"}</small>
                                </div>
                                <p class="mb-1"><strong>Predicted condition:</strong> ${assessment.predicted_condition || "Not specified"}</p>
                                <p class="bc-muted small mb-2">${assessment.assessment_summary || ""}</p>
                                <p class="small mb-1 fw-semibold">Recommended action</p>
                                <div class="small" id="reviewRecommendations">${buildRecommendationsHtml(assessmentData)}</div>
                                
                                <hr class="my-3">
                                <div class="small text-muted">
                                    <strong>Date:</strong> ${new Date(assessment.created_at).toLocaleString()}<br>
                                    <strong>Symptoms:</strong> ${(assessment.symptoms || []).join(", ") || "N/A"}
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Remove existing modal if any
            const existingModal = document.getElementById("assessmentReviewModal");
            if (existingModal) {
                existingModal.remove();
            }

            // Add modal to body
            document.body.insertAdjacentHTML("beforeend", modalHtml);

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById("assessmentReviewModal"));
            modal.show();

        } catch (err) {
            console.error("Failed to show assessment review:", err);
            showToast("Failed to load assessment details.", "danger");
        }
    }

    // Referrals (Resident view)
    async function loadReferrals() {
        const listEl = document.getElementById("bcReferralList");
        if (!listEl) return;
        listEl.innerHTML = '<div class="bc-skeleton" style="height: 100px; width: 100%; margin-bottom: 15px;"></div><div class="bc-skeleton" style="height: 100px; width: 100%;"></div>';
        try {
            const referrals = await apiCall("/referrals/me", { method: "GET" });
            if (!referrals || !referrals.length) {
                listEl.innerHTML = '<div class="bc-empty-state"><i class="bi bi-file-medical"></i><h6>No Referral Slips</h6><p class="small mb-0">You don\'t have any referral slips at the moment.</p></div>';
                return;
            }
            listEl.innerHTML = referrals
                .map(
                    (r) => {
                        const isCompleted = r.status === 'CLOSED' || r.status === 'ATTENDED';
                        const isExpired = r.is_expired;
                        const expiresAt = r.expires_at ? new Date(r.expires_at) : null;
                        const daysLeft = expiresAt ? Math.ceil((expiresAt - new Date()) / (1000 * 60 * 60 * 24)) : null;

                        // Build expiration badge
                        let expirationBadge = '';
                        if (isExpired) {
                            expirationBadge = '<span class="badge bg-danger"><i class="bi bi-exclamation-triangle"></i> EXPIRED</span>';
                        } else if (daysLeft !== null && daysLeft <= 2) {
                            expirationBadge = `<span class="badge bg-warning text-dark"><i class="bi bi-clock"></i> Expires in ${daysLeft}d</span>`;
                        } else if (expiresAt) {
                            expirationBadge = `<span class="badge bg-success"><i class="bi bi-calendar-check"></i> Valid until ${expiresAt.toLocaleDateString()}</span>`;
                        }

                        return `
                    <div class="bc-announcement-item">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <div class="fw-semibold">Referral ${r.referral_code}</div>
                                <div class="bc-muted small">${new Date(r.generated_at).toLocaleString()}</div>
                                <div class="small"><strong>Center:</strong> ${r.referred_to_center}</div>
                                <div class="small"><strong>Status:</strong> ${r.status} ${expirationBadge}</div>
                            </div>
                            <div class="text-end">
                                ${!isExpired && !isCompleted ? `<a class="btn btn-sm btn-outline-primary mb-1" href="/api/referrals/${r.id}/download" target="_blank">Download PDF</a>` : ''}
                                <button class="btn btn-sm btn-outline-info d-block" onclick="viewReferralSlip(${r.id}, '${r.referral_code}')">View Details</button>
                                ${isExpired ? '<span class="badge bg-danger d-block mt-1">Cannot Download</span>' : ''}
                                ${isCompleted ? '<span class="badge bg-secondary d-block mt-1">Completed</span>' : ''}
                            </div>
                        </div>
                    </div>
                `;
                    }
                )
                .join("");
        } catch (err) {
            console.error(err);
            listEl.innerHTML = `<p class="text-danger mb-0">Failed to load referrals: ${err.message}</p>`;
        }
    }

    const refreshReferralsBtn = document.getElementById("bcRefreshReferrals");
    if (refreshReferralsBtn) {
        refreshReferralsBtn.addEventListener("click", loadReferrals);
    }
    loadReferrals();

    // Consultation functions for residents
    async function requestConsultation(assessmentId, symptoms) {
        try {
            const response = await apiCall("/consultations/request", {
                method: "POST",
                body: JSON.stringify({
                    assessment_id: assessmentId,
                    symptoms: symptoms || []
                })
            });

            showToast("Consultation requested successfully! A BHW will review your case.", "success");

            // Update the button to show pending status
            const consultBtn = document.getElementById("bcConsultBtn");
            if (consultBtn) {
                consultBtn.innerHTML = '<i class="bi bi-clock"></i> CONSULTATION PENDING';
                consultBtn.classList.remove("btn-warning");
                consultBtn.classList.add("btn-secondary");
                consultBtn.disabled = true;
            }

        } catch (err) {
            console.error("Failed to request consultation:", err);
            showToast("Failed to request consultation: " + err.message, "danger");
        }
    }

    // Expose functions to global scope for onclick handlers
    window.requestConsultation = requestConsultation;
    window.viewReferralSlip = viewReferralSlip;
    window.viewResidentProfile = viewResidentProfile;
    window.editResidentProfile = editResidentProfile;
    window.downloadResidentProfile = downloadResidentProfile;
});
