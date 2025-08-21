// Scout Advancements Page JavaScript

// Load API utility
const script = document.createElement('script');
script.src = 'js/api.js';
script.onload = async function() {
    console.log('API utility loaded');
    await initializePage();
};
document.head.appendChild(script);

document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners
    addEventListeners();
});

async function initializePage() {
    // Load scout data
    const scoutData = await getScoutData();

    if (!scoutData) return; // User was redirected to signin

    // Update header stats
    updateHeaderStats(scoutData);

    // Set up rank tabs
    setupRankTabs();

    // Show current rank by default
    switchRank(scoutData.currentRank);
}

async function getScoutData() {
    try {
        // Check if user is authenticated
        if (!API.isAuthenticated()) {
            window.location.href = 'signin.html';
            return null;
        }

        // Get user data from token
        const userData = API.getUserFromToken();
        if (!userData) {
            window.location.href = 'signin.html';
            return null;
        }

        // For now, return mock data structure - we'll enhance this with real requirements data
        // TODO: Implement real requirements fetching for all ranks
        return {
            name: userData.email.split('@')[0], // Use email prefix as name
            currentRank: userData.role === 'scoutmaster' ? 'eagle' : 'tenderfoot', // Default ranks
            completedRequirements: 6,
            totalRequirements: 10,
            ranks: [
                {
                    id: 'scout',
                    name: 'Scout',
                    completed: true,
                    requirements: 5
                },
                {
                    id: 'tenderfoot',
                    name: 'Tenderfoot',
                    completed: false,
                    requirements: 10,
                    completedCount: 6
                },
                {
                    id: 'second_class',
                    name: 'Second Class',
                    completed: false,
                    requirements: 3,
                    completedCount: 0
                },
                {
                    id: 'first_class',
                    name: 'First Class',
                    completed: false,
                    requirements: 3,
                    completedCount: 0
                },
                {
                    id: 'star',
                    name: 'Star',
                    completed: false,
                    requirements: 3,
                    completedCount: 0
                },
                {
                    id: 'life',
                    name: 'Life',
                    completed: false,
                    requirements: 3,
                    completedCount: 0
                },
                {
                    id: 'eagle',
                    name: 'Eagle',
                    completed: false,
                    requirements: 4,
                    completedCount: 0
                }
            ]
        };
    } catch (error) {
        console.error('Error fetching scout data:', error);
        showNotification('Error loading advancement data. Please refresh the page.', 'error');

        // Return fallback data
        return {
            name: 'Scout',
            currentRank: 'tenderfoot',
            completedRequirements: 0,
            totalRequirements: 10,
            ranks: []
        };
    }
}

function updateHeaderStats(data) {
    document.getElementById('currentRankDisplay').textContent = data.currentRank.charAt(0).toUpperCase() + data.currentRank.slice(1);
    document.getElementById('completedReqs').textContent = `${data.completedRequirements}/${data.totalRequirements}`;
    document.getElementById('progressPercent').textContent = `${Math.round((data.completedRequirements / data.totalRequirements) * 100)}%`;
}

function setupRankTabs() {
    const rankTabs = document.querySelectorAll('.rank-tab');
    rankTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const rankId = this.textContent.toLowerCase().replace(' ', '_');
            switchRank(rankId);
        });
    });
}

function switchRank(rankId) {
    // Remove active class from all tabs and requirements
    document.querySelectorAll('.rank-tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.rank-requirements').forEach(req => req.classList.remove('active'));

    // Add active class to selected tab and requirements
    const activeTab = document.querySelector(`[onclick="switchRank('${rankId}')"]`);
    if (activeTab) {
        activeTab.classList.add('active');
    }

    const activeRequirements = document.getElementById(`${rankId}-requirements`);
    if (activeRequirements) {
        activeRequirements.classList.add('active');
    }
}

function addEventListeners() {
    // Sign out button
    const signOutBtn = document.querySelector('.btn-secondary');
    if (signOutBtn) {
        signOutBtn.addEventListener('click', function() {
            if (confirm('Are you sure you want to sign out?')) {
                API.logout(); // This will redirect to signin.html
            }
        });
    }

    // Navigation links
    const navLinks = document.querySelectorAll('.dashboard-nav .nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (this.textContent !== 'Advancements') {
                e.preventDefault();
                showNotification(`${this.textContent} page coming soon!`, 'info');
            }
        });
    });
}

// Action functions
async function requestSignoff(requirementName, rank, requirementNumber, requirementId) {
    if (confirm(`Request sign-off for "${requirementName}"?`)) {
        try {
            await API.createSignoffRequest(requirementId);
            showNotification(`Sign-off requested for ${requirementName}!`, 'success');

            // Update button to show pending state
            const button = event.target;
            button.textContent = 'Pending';
            button.className = 'btn btn-outline';
            button.disabled = true;
        } catch (error) {
            console.error('Error requesting signoff:', error);
            showNotification('Error requesting sign-off. Please try again.', 'error');
        }
    }
}

async function requestConference(rank) {
    const rankNames = {
        'scout': 'Scout',
        'tenderfoot': 'Tenderfoot',
        'second_class': 'Second Class',
        'first_class': 'First Class',
        'star': 'Star',
        'life': 'Life',
        'eagle': 'Eagle'
    };

    const rankName = rankNames[rank] || rank;
    if (confirm(`Request a Scoutmaster conference for your ${rankName} rank?`)) {
        try {
            await API.createConferenceRequest('scoutmaster_conference', rank);
            showNotification(`Scoutmaster conference requested for ${rankName} rank!`, 'success');
        } catch (error) {
            console.error('Error requesting conference:', error);
            showNotification('Error requesting conference. Please try again.', 'error');
        }
    }
}

async function requestBoardOfReview(rank) {
    const rankNames = {
        'second_class': 'Second Class',
        'first_class': 'First Class',
        'star': 'Star',
        'life': 'Life',
        'eagle': 'Eagle'
    };

    const rankName = rankNames[rank] || rank;
    if (confirm(`Request a Board of Review for your ${rankName} rank?`)) {
        try {
            await API.createConferenceRequest('board_of_review', rank);
            showNotification(`Board of Review requested for ${rankName} rank!`, 'success');
        } catch (error) {
            console.error('Error requesting board of review:', error);
            showNotification('Error requesting board of review. Please try again.', 'error');
        }
    }
}

// Admin functions (for admin users)
function addRequirement() {
    if (!isAdmin()) {
        showNotification('Only administrators can add requirements.', 'error');
        return;
    }

    const requirementText = prompt('Enter the requirement description:');
    const rank = prompt('Enter the rank (scout, tenderfoot, second_class, first_class, star, life, eagle):');
    const lesson = prompt('Enter the lesson/learning objective:');

    if (requirementText && rank && lesson) {
        showNotification(`New requirement added to ${rank} rank!`, 'success');
    }
}

function editRequirement(requirementId) {
    if (!isAdmin()) {
        showNotification('Only administrators can edit requirements.', 'error');
        return;
    }

    const newText = prompt('Enter the new requirement text:');
    if (newText) {
        showNotification('Requirement updated successfully!', 'success');
    }
}

function deleteRequirement(requirementId) {
    if (!isAdmin()) {
        showNotification('Only administrators can delete requirements.', 'error');
        return;
    }

    if (confirm('Are you sure you want to delete this requirement?')) {
        showNotification('Requirement deleted successfully!', 'success');
    }
}

function isAdmin() {
    // Check if the current user has admin privileges using JWT token
    const userData = API.getUserFromToken();
    if (!userData) return false;

    // For now, check if user is scoutmaster (admin role)
    // This could be extended to check for specific admin permissions
    return userData.role === 'scoutmaster';
}

// Notification system
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;

    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        min-width: 300px;
        max-width: 500px;
    `;

    const content = notification.querySelector('.notification-content');
    content.style.cssText = `
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        border-radius: 8px;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    `;

    // Set colors based on type
    if (type === 'success') {
        content.style.background = 'linear-gradient(135deg, #00D4FF, #0078FF)';
        content.style.color = 'white';
    } else if (type === 'error') {
        content.style.background = 'linear-gradient(135deg, #ff4444, #cc3333)';
        content.style.color = 'white';
    } else {
        content.style.background = 'var(--bg-tertiary)';
        content.style.color = 'var(--text-primary)';
        content.style.border = '1px solid var(--border-color)';
    }

    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.style.cssText = `
        background: none;
        border: none;
        color: inherit;
        font-size: 20px;
        cursor: pointer;
        padding: 0;
        margin-left: 12px;
    `;

    // Add to page
    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
}

// Add notification styles to head
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    .notification {
        animation: slideIn 0.3s ease-out;
    }

    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(notificationStyles);
