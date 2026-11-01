/**
 * Recruitment & Placement Management System
 * Interactive Client-Side Utilities
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Mobile Sidebar Toggle
  const toggleBtn = document.getElementById("sidebarToggle");
  const sidebar = document.querySelector(".sidebar");
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", function () {
      sidebar.classList.toggle("open");
    });
  }

  // 2. Demo Login Quick Fill
  document.querySelectorAll(".demo-cred-row").forEach(function (row) {
    row.addEventListener("click", function () {
      const username = this.getAttribute("data-username");
      const password = this.getAttribute("data-password");
      const userInput = document.getElementById("username");
      const passInput = document.getElementById("password");
      if (userInput && passInput) {
        userInput.value = username;
        passInput.value = password;
      }
    });
  });

  // 3. Dynamic Eligibility Checker on Application Form
  const candidateSelect = document.getElementById("candidate_id");
  const jobSelect = document.getElementById("job_id");
  const eligibilityBox = document.getElementById("eligibility-preview");

  function checkEligibility() {
    if (!candidateSelect || !jobSelect || !eligibilityBox) return;

    const candId = candidateSelect.value;
    const jobId = jobSelect.value;

    if (!candId || !jobId) {
      eligibilityBox.innerHTML = `
        <div class="alert alert-info">
          Select both a Candidate and a Job Opening above to evaluate real-time eligibility criteria.
        </div>
      `;
      return;
    }

    eligibilityBox.innerHTML = `
      <div class="alert alert-info">
        Evaluating eligibility criteria against database rules...
      </div>
    `;

    fetch(`/api/check-eligibility?candidate_id=${encodeURIComponent(candId)}&job_id=${encodeURIComponent(jobId)}`)
      .then(response => response.json())
      .then(data => {
        if (!data.success) {
          eligibilityBox.innerHTML = `
            <div class="alert alert-danger">
              Error checking eligibility: ${data.message}
            </div>
          `;
          return;
        }

        const isEligible = data.is_eligible;
        const alertClass = isEligible ? "alert-success" : "alert-warning";
        const badgeClass = isEligible ? "badge-eligible" : "badge-not_eligible";
        const titleText = isEligible ? "Candidate is ELIGIBLE" : "Candidate is NOT ELIGIBLE";

        let reasonsList = data.reasons.map(r => `<li>${r}</li>`).join("");

        let overridePrompt = "";
        const overrideSection = document.getElementById("override-section");
        if (!isEligible) {
          if (overrideSection) overrideSection.style.display = "block";
          overridePrompt = `
            <p class="form-text" style="color: var(--danger-text); margin-top: 8px;">
              <strong>Note:</strong> Authorized staff can submit this application only with an explicit override reason below.
            </p>
          `;
        } else {
          if (overrideSection) overrideSection.style.display = "none";
        }

        eligibilityBox.innerHTML = `
          <div class="alert ${alertClass}">
            <div style="width: 100%;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                <strong>${titleText}</strong>
                <span class="badge ${badgeClass}">${data.status}</span>
              </div>
              <ul style="padding-left: 20px; font-size: 0.85rem;">
                ${reasonsList}
              </ul>
              ${overridePrompt}
            </div>
          </div>
        `;
      })
      .catch(err => {
        eligibilityBox.innerHTML = `
          <div class="alert alert-danger">
            Network error checking eligibility.
          </div>
        `;
      });
  }

  if (candidateSelect && jobSelect) {
    candidateSelect.addEventListener("change", checkEligibility);
    jobSelect.addEventListener("change", checkEligibility);
    // Initial check if values are pre-selected
    if (candidateSelect.value && jobSelect.value) {
      checkEligibility();
    }
  }

  // 4. Confirmation dialog helper
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      const msg = this.getAttribute("data-confirm") || "Are you sure you want to perform this action?";
      if (!confirm(msg)) {
        e.preventDefault();
      }
    });
  });
});

