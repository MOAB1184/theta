// Scout Dashboard JavaScript

// Load API utility
const script = document.createElement('script');
script.src = 'js/api.js';
script.onload = async function() {
    console.log('API utility loaded');
    await initializeDashboard();
};
document.head.appendChild(script);

document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners
    addEventListeners();
});

async function initializeDashboard() {
    // Load scout data
    const scoutData = await getScoutData();

    if (!scoutData) return; // User was redirected to signin

    // Update welcome section
    updateWelcomeSection(scoutData);

    // Update progress cards
    updateProgressCards(scoutData);

    // Update rank timeline
    updateRankTimeline(scoutData);

    // Initialize interactive elements
    initializeInteractiveElements();
}

async function getScoutData() {
    try {
        // Check if user is authenticated
        if (!API.isAuthenticated()) {
            window.location.href = 'signin.html';
            return null;
        }

        // Fetch real data from API
        const data = await API.getScoutDashboard();

        return {
            name: data.user.name,
            troopNumber: data.user.troop_number,
            currentRank: data.user.current_rank,
            currentRankName: data.user.current_rank.charAt(0).toUpperCase() + data.user.current_rank.slice(1).replace('_', ' '),
            completedRequirements: data.user.completed_requirements,
            totalRequirements: data.user.total_requirements,
            ranksCompleted: data.user.ranks_completed,
            totalRanks: 9, // Standard BSA ranks
            eagleProgress: data.user.eagle_progress,
            recentActivity: data.recent_activity || []
        };
    } catch (error) {
        console.error('Error fetching scout data:', error);
        showNotification('Error loading dashboard data. Please refresh the page.', 'error');

        // Return fallback data
        return {
            name: 'Scout',
            troopNumber: 'Unknown',
            currentRank: 'unranked',
            currentRankName: 'Unranked',
            completedRequirements: 0,
            totalRequirements: 0,
            ranksCompleted: 0,
            totalRanks: 9,
            eagleProgress: 0,
            recentActivity: []
        };
    }
}

function updateWelcomeSection(data) {
    document.getElementById('scoutName').textContent = data.name;
    document.getElementById('troopNumber').textContent = data.troopNumber;
}

function updateProgressCards(data) {
    // Update current rank display
    document.getElementById('currentRankBadge').innerHTML = getRankBadge(data.currentRank);
    document.getElementById('currentRankName').textContent = data.currentRankName;

    // Update progress bar
    const progressPercentage = (data.completedRequirements / data.totalRequirements) * 100;
    document.getElementById('rankProgressBar').style.width = progressPercentage + '%';
    document.getElementById('rankProgressText').textContent = `${data.completedRequirements}/${data.totalRequirements} completed`;

    // Update Eagle progress
    document.getElementById('ranksCompleted').textContent = data.ranksCompleted;
    document.getElementById('eagleProgressBar').style.width = data.eagleProgress + '%';

    // Update recent activity
    updateActivityList(data.recentActivity);
}

function getRankBadge(rank) {
    const rankBadges = {
        'scout': 'S',
        'tenderfoot': 'T',
        'second_class': '2',
        'first_class': '1',
        'star': '★',
        'life': '◉',
        'eagle': 'E'
    };
    return rankBadges[rank] || rank.charAt(0).toUpperCase();
}

function updateActivityList(activities) {
    const activityList = document.querySelector('.activity-list');
    activityList.innerHTML = '';

    activities.forEach(activity => {
        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';
        activityItem.innerHTML = `
            <div class="activity-icon">${getActivityIcon(activity.type)}</div>
            <div class="activity-content">
                <h5>${activity.title}</h5>
                <p>${activity.description}</p>
                <span class="activity-time">${activity.time}</span>
            </div>
        `;
        activityList.appendChild(activityItem);
    });
}

function getActivityIcon(type) {
    const icons = {
        'signoff_approved': '✓',
        'signoff_pending': '⏰',
        'rank_progress': '🎯',
        'conference': '🏆'
    };
    return icons[type] || '📋';
}

function updateRankTimeline(data) {
    // Mark completed ranks
    const timelineItems = document.querySelectorAll('.timeline-item');
    timelineItems.forEach((item, index) => {
        if (index < data.ranksCompleted) {
            item.classList.add('completed');
        } else if (index === data.ranksCompleted) {
            item.classList.add('active');
        }
    });
}

function addEventListeners() {
    // Navigation links
    const navLinks = document.querySelectorAll('.dashboard-nav .nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Remove active class from all links
            navLinks.forEach(l => l.classList.remove('active'));
            // Add active class to clicked link
            this.classList.add('active');

            // Here you would normally handle navigation
            // For now, just show an alert
            if (this.textContent !== 'Dashboard') {
                showNotification(`${this.textContent} page coming soon!`, 'info');
            }
        });
    });

    // Sign out button
    const signOutBtn = document.querySelector('.btn-secondary');
    if (signOutBtn) {
        signOutBtn.addEventListener('click', function() {
            if (confirm('Are you sure you want to sign out?')) {
                API.logout(); // This will redirect to signin.html
            }
        });
    }

    // Action buttons
    const actionButtons = document.querySelectorAll('.action-btn');
    actionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.textContent.trim().toLowerCase();
            handleAction(action);
        });
    });
}

function handleAction(action) {
    switch (action) {
        case 'view requirements':
            window.location.href = 'advancements.html';
            break;
        case 'sign-off requests':
            showNotification('Sign-off requests page coming soon!', 'info');
            break;
        case 'request conference':
            requestConference();
            break;
        case 'request board of review':
            requestBoardOfReview();
            break;
        default:
            showNotification(`Action: ${action}`, 'info');
    }
}

async function requestConference() {
    const scoutData = await getScoutData();
    if (!scoutData) return;

    if (confirm('Request a Scoutmaster conference for your current rank?')) {
        try {
            await API.createConferenceRequest('scoutmaster_conference', scoutData.currentRank);
            showNotification('Scoutmaster conference requested successfully! You will be notified when it\'s scheduled.', 'success');
        } catch (error) {
            console.error('Error requesting conference:', error);
            showNotification('Error requesting conference. Please try again.', 'error');
        }
    }
}

async function requestBoardOfReview() {
    const scoutData = await getScoutData();
    if (!scoutData) return;

    if (confirm('Request a Board of Review for your current rank? This is typically done when you\'ve completed all requirements.')) {
        try {
            await API.createConferenceRequest('board_of_review', scoutData.currentRank);
            showNotification('Board of Review requested successfully! You will be notified when it\'s scheduled.', 'success');
        } catch (error) {
            console.error('Error requesting board of review:', error);
            showNotification('Error requesting board of review. Please try again.', 'error');
        }
    }
}

function initializeInteractiveElements() {
    // Add hover effects to progress cards
    const progressCards = document.querySelectorAll('.progress-card');
    progressCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Add click effects to timeline items
    const timelineItems = document.querySelectorAll('.timeline-item');
    timelineItems.forEach(item => {
        item.addEventListener('click', function() {
            const rankName = this.querySelector('h4').textContent;
            showNotification(`${rankName} rank - Click to view details`, 'info');
        });
    });
}

function simulateLiveUpdates() {
    // Simulate periodic updates (in a real app, this would be WebSocket or Server-Sent Events)
    setInterval(() => {
        // Randomly update progress (for demo purposes)
        const progressBar = document.getElementById('rankProgressBar');
        const currentWidth = parseFloat(progressBar.style.width);
        if (currentWidth < 100 && Math.random() < 0.1) { // 10% chance
            const newWidth = Math.min(currentWidth + 5, 100);
            progressBar.style.width = newWidth + '%';
            document.getElementById('rankProgressText').textContent = `${Math.round(newWidth / 10)}/10 completed`;
        }
    }, 5000);
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
