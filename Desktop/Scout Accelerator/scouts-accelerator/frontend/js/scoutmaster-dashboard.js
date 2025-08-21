// Scoutmaster Dashboard JavaScript

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

// Initialize dashboard data
async function initializeDashboard() {
    // Load scoutmaster data
    const data = await getScoutmasterData();

    if (!data) return; // User was redirected to signin

    // Update welcome section
    updateWelcomeSection(data);

    // Update overview cards
    updateOverviewCards(data);

    // Update management sections
    updateManagementSections(data);
}

async function getScoutmasterData() {
    try {
        // Check if user is authenticated
        if (!API.isAuthenticated()) {
            window.location.href = 'signin.html';
            return null;
        }

        // Fetch real data from API
        const data = await API.getScoutmasterDashboard();

        return {
            name: data.troop.created_by_name || 'Scoutmaster',
            troopCode: data.troop.code,
            troopName: data.troop.name,
            totalScouts: data.stats.total_scouts,
            activePatrols: data.stats.active_patrols,
            pendingSignoffs: data.stats.pending_signoffs,
            upcomingEvents: data.stats.upcoming_events,
            pendingSignoffsList: data.pending_signoffs || [],
            conferenceRequests: data.conference_requests || [],
            members: [], // Will be loaded separately
            patrols: [], // TODO: Implement patrols endpoint
            eligibleRank: data.troop.eligible_signoff_rank || 'first_class'
        };
    } catch (error) {
        console.error('Error fetching scoutmaster data:', error);
        showNotification('Error loading dashboard data. Please refresh the page.', 'error');

        // Return fallback data
        return {
            name: 'Scoutmaster',
            troopCode: 'Unknown',
            troopName: 'Unknown Troop',
            totalScouts: 0,
            activePatrols: 0,
            pendingSignoffs: 0,
            upcomingEvents: 0,
            pendingSignoffsList: [],
            conferenceRequests: [],
            members: [],
            patrols: [],
            eligibleRank: 'first_class'
        };
    }
}

function updateWelcomeSection(data) {
    document.getElementById('scoutmasterName').textContent = data.name;
    document.getElementById('troopCode').textContent = data.troopCode;
}

function updateOverviewCards(data) {
    // Update stats
    document.getElementById('totalScouts').textContent = data.totalScouts;
    document.getElementById('activePatrols').textContent = data.activePatrols;
    document.getElementById('pendingSignoffs').textContent = data.pendingSignoffs;
    document.getElementById('upcomingEvents').textContent = data.upcomingEvents;

    // Update signoff requests
    updateSignoffRequests(data.pendingSignoffsList);

    // Update conference requests
    updateConferenceRequests(data.conferenceRequests);
}

function updateSignoffRequests(requests) {
    const container = document.getElementById('pendingSignoffsList');
    container.innerHTML = '';

    requests.forEach(request => {
        const item = document.createElement('div');
        item.className = 'signoff-item';
        item.innerHTML = `
            <div class="signoff-info">
                <h5>${request.scout}</h5>
                <p>${request.requirement}</p>
                <span class="signoff-time">${request.time}</span>
            </div>
            <div class="signoff-actions">
                <button class="btn-approve" onclick="approveSignoff(this)" data-signoff-id="${request.id}">✓</button>
                <button class="btn-deny" onclick="denySignoff(this)" data-signoff-id="${request.id}">✗</button>
            </div>
        `;
        container.appendChild(item);
    });
}

function updateConferenceRequests(requests) {
    const container = document.getElementById('conferenceRequestsList');
    container.innerHTML = '';

    requests.forEach(request => {
        const item = document.createElement('div');
        item.className = 'conference-item';
        item.innerHTML = `
            <div class="conference-info">
                <h5>${request.scout}</h5>
                <p>${request.type}</p>
                <span class="conference-status status-${request.status}">
                    ${request.status === 'scheduled' ? `Scheduled for ${request.scheduled}` : 'Pending'}
                </span>
            </div>
            <div class="conference-actions">
                ${request.status === 'pending' ?
                    `<button class="btn-schedule" onclick="scheduleConference(this)" data-conference-id="${request.id}">Schedule</button>` :
                    '<button class="btn-complete" onclick="completeConference(this)">Complete</button>'
                }
            </div>
        `;
        container.appendChild(item);
    });
}

function updateManagementSections(data) {
    // Update members list (load real data)
    loadMembersList();

    // Update patrols list
    updatePatrolsList(data.patrols);

    // Update settings
    document.getElementById('eligibleRank').value = data.eligibleRank;
}

async function loadMembersList() {
    try {
        const response = await API.getTroopMembers();
        updateMembersList(response.members);
    } catch (error) {
        console.error('Error loading members:', error);
        showNotification('Error loading troop members', 'error');
    }
}

function updateMembersList(members) {
    const container = document.querySelector('.members-list');
    container.innerHTML = '';

    members.forEach(member => {
        const item = document.createElement('div');
        item.className = 'member-item';
        item.innerHTML = `
            <div class="member-info">
                <div class="member-avatar">${getInitials(member.full_name)}</div>
                <div class="member-details">
                    <h5>${member.full_name}</h5>
                    <span class="member-rank">${member.role}</span>
                    <span class="member-rank-progress">${member.current_rank}</span>
                </div>
            </div>
            <div class="member-actions">
                ${member.role !== 'scoutmaster' ?
                    `<span class="member-status status-active">Active</span>
                     <button class="btn-remove" onclick="removeMember('${member.id}', '${member.full_name}')">Remove</button>` :
                    `<span class="member-status status-active">Scoutmaster</span>`
                }
            </div>
        `;
        container.appendChild(item);
    });
}

function updatePatrolsList(patrols) {
    const container = document.querySelector('.patrols-list');
    container.innerHTML = '';

    patrols.forEach(patrol => {
        const item = document.createElement('div');
        item.className = 'patrol-item';
        item.innerHTML = `
            <div class="patrol-info">
                <div class="patrol-name">
                    <h5>${patrol.name}</h5>
                    <span class="patrol-leader">Leader: ${patrol.leader}</span>
                </div>
                <div class="patrol-stats">
                    <span class="patrol-members">${patrol.members} members</span>
                </div>
            </div>
            <div class="patrol-actions">
                <button class="btn-manage" onclick="managePatrol(this)">Manage</button>
            </div>
        `;
        container.appendChild(item);
    });
}

function getInitials(name) {
    return name.split(' ').map(n => n[0]).join('').toUpperCase();
}

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// Event listeners
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
}

// Action functions
function copyTroopCode() {
    const troopCode = document.getElementById('troopCode').textContent;
    navigator.clipboard.writeText(troopCode).then(() => {
        showNotification('Troop code copied to clipboard!', 'success');
    });
}

function renameTroop() {
    const newName = prompt('Enter new troop name:');
    if (newName && newName.trim()) {
        showNotification(`Troop renamed to "${newName.trim()}"`, 'success');
    }
}

async function approveSignoff(button) {
    const item = button.closest('.signoff-item');
    const scoutName = item.querySelector('h5').textContent;
    const signoffId = button.getAttribute('data-signoff-id');

    try {
        await API.approveSignoff(signoffId);
        item.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => {
            item.remove();
            showNotification(`Sign-off approved for ${scoutName}!`, 'success');
        }, 300);
    } catch (error) {
        console.error('Error approving signoff:', error);
        showNotification('Error approving sign-off', 'error');
    }
}

async function denySignoff(button) {
    const item = button.closest('.signoff-item');
    const scoutName = item.querySelector('h5').textContent;
    const signoffId = button.getAttribute('data-signoff-id');

    const reason = prompt(`Why are you denying ${scoutName}'s sign-off request?`);
    if (reason !== null) {
        try {
            await API.rejectSignoff(signoffId, reason);
            item.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => {
                item.remove();
                showNotification(`Sign-off denied for ${scoutName}`, 'info');
            }, 300);
        } catch (error) {
            console.error('Error denying signoff:', error);
            showNotification('Error denying sign-off', 'error');
        }
    }
}

async function scheduleConference(button) {
    const item = button.closest('.conference-item');
    const scoutName = item.querySelector('h5').textContent;
    const conferenceId = button.getAttribute('data-conference-id');

    // Simple date/time picker (in real app, use a proper date picker)
    const date = prompt('Enter date and time for conference (e.g., "March 15, 2:00 PM"):');
    if (date) {
        try {
            await API.scheduleConference(conferenceId, date);

            const status = item.querySelector('.conference-status');
            status.textContent = `Scheduled for ${date}`;
            status.className = 'conference-status status-scheduled';

            button.textContent = 'Complete';
            button.className = 'btn-complete';
            button.onclick = function() { completeConference(this); };

            showNotification(`Conference scheduled for ${scoutName} on ${date}`, 'success');
        } catch (error) {
            console.error('Error scheduling conference:', error);
            showNotification('Error scheduling conference', 'error');
        }
    }
}

function completeConference(button) {
    const item = button.closest('.conference-item');
    const scoutName = item.querySelector('h5').textContent;

    item.style.animation = 'fadeOut 0.3s ease';
    setTimeout(() => {
        item.remove();
        showNotification(`Conference completed for ${scoutName}!`, 'success');
    }, 300);
}

async function removeMember(memberId, memberName) {
    if (confirm(`Are you sure you want to remove ${memberName} from the troop?`)) {
        try {
            await API.removeMember(memberId);
            showNotification(`${memberName} has been removed from the troop`, 'success');
            // Reload members list
            loadMembersList();
        } catch (error) {
            console.error('Error removing member:', error);
            showNotification('Error removing member from troop', 'error');
        }
    }
}

function managePatrol(button) {
    const item = button.closest('.patrol-item');
    const patrolName = item.querySelector('h5').textContent;

    showNotification(`${patrolName} management panel coming soon!`, 'info');
}

function openManagementPanel() {
    showNotification('Troop management panel coming soon!', 'info');
}

function addMember() {
    const name = prompt('Enter scout name:');
    const role = prompt('Enter scout role (e.g., Scout, Tenderfoot, etc.):');

    if (name && role) {
        showNotification(`${name} has been added as ${role}`, 'success');
        // In real app, this would refresh the members list
    }
}

function createPatrol() {
    const name = prompt('Enter patrol name:');
    const leader = prompt('Enter patrol leader name:');

    if (name && leader) {
        showNotification(`Patrol "${name}" created with leader ${leader}`, 'success');
        // In real app, this would refresh the patrols list
    }
}

function updateEligibleRank(rank) {
    showNotification(`Eligible sign-off rank updated to ${rank.replace('_', ' ')}`, 'success');
}

function assignSPL(scoutId) {
    if (scoutId) {
        const scoutName = document.querySelector(`#splSelect option[value="${scoutId}"]`).textContent;
        showNotification(`${scoutName} has been assigned as Senior Patrol Leader`, 'success');
    }
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

    @keyframes fadeOut {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(-10px);
        }
    }
`;
document.head.appendChild(notificationStyles);
