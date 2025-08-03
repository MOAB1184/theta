// Shared navigation functionality for Canvas AI
document.addEventListener('DOMContentLoaded', () => {
    // --- ELEMENT REFERENCES ---
    const themeToggleBtns = document.querySelectorAll('.theme-toggle-btn');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    const menuToggle = document.getElementById('menu-toggle-btn');
    const navLinks = document.querySelectorAll('.nav-link');

    // --- NAVIGATION MAPPING ---
    const pageMapping = {
        'home': 'home.html',
        'ai-agent': 'Ai Agent.html',
        'notes': 'notes.html',
        'calendar': 'calander.html',
        'assignments': 'Assignments.html',
        'student-planner': 'home.html', // Redirects to home for now
        'autocomplete-hw': 'AutoHw.html',
        'ai-class-notes': 'home.html', // Redirects to home for now
        'ai-tutor': 'home.html', // Redirects to home for now
        'settings': 'settings.html'
    };

    // --- NAVIGATION FUNCTIONALITY ---
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.getAttribute('data-view');
            
            if (view && pageMapping[view]) {
                // Navigate to the appropriate page
                window.location.href = pageMapping[view];
            }
        });
    });

    // --- THEME TOGGLE LOGIC ---
    const updateTheme = (isDarkMode) => {
        document.body.classList.toggle('dark-mode', isDarkMode);
        localStorage.setItem('darkMode', isDarkMode);
        themeToggleBtns.forEach(btn => {
            if (btn.querySelector('span')) {
                btn.querySelector('span').textContent = isDarkMode ? 'Light Mode' : 'Dark Mode';
            }
        });
    };

    themeToggleBtns.forEach(btn => btn.addEventListener('click', () => {
        const isCurrentlyDark = document.body.classList.contains('dark-mode');
        updateTheme(!isCurrentlyDark);
    }));

    // Check for saved theme preference on load
    const savedDarkMode = localStorage.getItem('darkMode');
    if (savedDarkMode !== 'false') { // Default to dark mode if not set
        updateTheme(true);
    } else {
        updateTheme(false);
    }

    // --- SIDEBAR INTERACTIVITY LOGIC ---
    sidebarToggleBtn?.addEventListener('click', () => {
        const isCollapsed = sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('sidebar-collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed);
        sidebarToggleBtn.querySelector('span').textContent = isCollapsed ? 'Expand' : 'Collapse';
        const iconPolyline = sidebarToggleBtn.querySelector('polyline');
        if (iconPolyline) {
            iconPolyline.setAttribute('points', isCollapsed ? '9 18 15 12 9 6' : '15 18 9 12 15 6');
        }
    });

    // Check for saved sidebar state
    const savedSidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (savedSidebarCollapsed) {
        sidebar.classList.add('collapsed');
        mainContent.classList.add('sidebar-collapsed');
        sidebarToggleBtn.querySelector('span').textContent = 'Expand';
        const iconPolyline = sidebarToggleBtn.querySelector('polyline');
        if (iconPolyline) iconPolyline.setAttribute('points', '9 18 15 12 9 6');
    }

    // Mobile menu toggle
    menuToggle?.addEventListener('click', () => sidebar.classList.toggle('open'));
    
    // Close sidebar on link click (mobile)
    navLinks.forEach(link => {
        link.addEventListener('click', () => sidebar.classList.remove('open'));
    });

    // --- SET ACTIVE NAVIGATION ITEM ---
    const setActiveNavItem = () => {
        // Get current page filename
        const currentPage = window.location.pathname.split('/').pop();
        
        // Remove active class from all nav links
        navLinks.forEach(link => link.classList.remove('active'));
        
        // Special case for home.html and root path - only highlight "home"
        if (currentPage === 'home.html' || currentPage === '' || currentPage === 'index.html' || currentPage === '/') {
            const homeLink = document.querySelector('[data-view="home"]');
            if (homeLink) homeLink.classList.add('active');
            return; // Exit early for home page
        }
        
        // For other pages, find the nav link that maps to the current page
        navLinks.forEach(link => {
            const view = link.getAttribute('data-view');
            if (view && pageMapping[view] === currentPage) {
                link.classList.add('active');
            }
        });
    };

    // Set active navigation item on page load
    setActiveNavItem();
}); 