// Add follow-up notification API functions
async function getMyFollowUps() {
    return apiCall("/follow-up/my-notifications");
}

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
