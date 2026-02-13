/**
 * AGUSTINA FALCON - MAIN JAVASCRIPT
 * Handles smooth scroll, animations, form validation, and interactivity
 */

'use strict';

// ============================================
// CONFIGURATION
// ============================================

const CONFIG = {
    animationDuration: 300,
    scrollThreshold: 50,
    debounceDelay: 150,
};

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Debounce function to limit execution frequency
 * @param {Function} func - Function to debounce
 * @param {Number} delay - Delay in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, delay) {
    let timeoutId = null;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func(...args), delay);
    };
}

/**
 * Throttle function to limit execution frequency
 * @param {Function} func - Function to throttle
 * @param {Number} limit - Time limit in milliseconds
 * @returns {Function} Throttled function
 */
function throttle(func, limit) {
    let inThrottle;
    return function (...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => (inThrottle = false), limit);
        }
    };
}

/**
 * Scroll element into view with smooth behavior
 * @param {String} selector - Element selector
 */
function smoothScroll(selector) {
    const element = document.querySelector(selector);
    if (element) {
        const headerOffset = 80;
        const elementPosition = element.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
        
        window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
        });
    }
}

/**
 * Check if element is in viewport
 * @param {Element} element - Element to check
 * @returns {Boolean}
 */
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top < (window.innerHeight || document.documentElement.clientHeight) &&
        rect.bottom > 0
    );
}

// ============================================
// NAVBAR SCROLL EFFECT
// ============================================

class NavbarScroll {
    constructor() {
        this.navbar = document.querySelector('.navbar-elegant');
        this.lastScrollPosition = 0;
        this.isScrolling = false;

        if (this.navbar) {
            this.init();
        }
    }

    init() {
        window.addEventListener(
            'scroll',
            throttle(() => this.handleScroll(), 100)
        );
    }

    handleScroll() {
        const currentScrollPosition = window.pageYOffset || document.documentElement.scrollTop;

        if (currentScrollPosition > CONFIG.scrollThreshold) {
            this.navbar.classList.add('scrolled');
        } else {
            this.navbar.classList.remove('scrolled');
        }

        this.lastScrollPosition = currentScrollPosition <= 0 ? 0 : currentScrollPosition;
    }
}

// ============================================
// SCROLL ANIMATIONS
// ============================================

class ScrollAnimations {
    constructor() {
        this.observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -100px 0px',
        };
        this.init();
    }

    init() {
        this.observeElements();
    }

    observeElements() {
        if (!('IntersectionObserver' in window)) {
            // Fallback for browsers that don't support IntersectionObserver
            this.addAnimationsDirectly();
            return;
        }

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    this.triggerAnimation(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, this.observerOptions);

        document.querySelectorAll('[data-animation]').forEach((element) => {
            observer.observe(element);
        });

        // Animate cards and features on scroll
        document.querySelectorAll('.feature-card, .stat-card, .benefit-item').forEach((element) => {
            observer.observe(element);
        });
    }

    triggerAnimation(element) {
        const animationType = element.dataset.animation;
        element.classList.add('animate__animated', `animate__${animationType}`);
    }

    addAnimationsDirectly() {
        document.querySelectorAll('[data-animation], .feature-card, .stat-card, .benefit-item').forEach((element) => {
            element.classList.add('fade-in');
        });
    }
}

// ============================================
// SMOOTH SCROLL FOR NAVIGATION LINKS
// ============================================

class SmoothNavigation {
    constructor() {
        this.init();
    }

    init() {
        document.querySelectorAll('a[href^="#"]').forEach((link) => {
            link.addEventListener('click', (e) => this.handleAnchorClick(e));
        });
    }

    handleAnchorClick(e) {
        const href = e.currentTarget.getAttribute('href');

        // Ignore if it's just "#" or empty
        if (href === '#' || href === '') {
            return;
        }

        e.preventDefault();

        const targetElement = document.querySelector(href);
        if (targetElement) {
            smoothScroll(href);

            // Close mobile menu if open
            const navbarCollapse = document.querySelector('.navbar-collapse');
            if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                const bsCollapse = new bootstrap.Collapse(navbarCollapse);
                bsCollapse.hide();
            }
        }
    }
}

// ============================================
// FORM VALIDATION
// ============================================

class FormValidator {
    constructor() {
        this.init();
    }

    init() {
        const forms = document.querySelectorAll('form');
        forms.forEach((form) => {
            form.addEventListener('submit', (e) => this.handleSubmit(e));
        });
    }

    handleSubmit(e) {
        e.preventDefault();
        const form = e.target;

        if (this.validateForm(form)) {
            this.submitForm(form);
        }
    }

    validateForm(form) {
        let isValid = true;

        form.querySelectorAll('[required]').forEach((input) => {
            if (!this.validateInput(input)) {
                isValid = false;
                this.showError(input);
            } else {
                this.clearError(input);
            }
        });

        return isValid;
    }

    validateInput(input) {
        const value = input.value.trim();

        if (value === '') {
            return false;
        }

        if (input.type === 'email') {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(value);
        }

        return true;
    }

    showError(input) {
        input.classList.add('is-invalid');
        const feedback = input.nextElementSibling;
        if (feedback && feedback.classList.contains('invalid-feedback')) {
            feedback.style.display = 'block';
        }
    }

    clearError(input) {
        input.classList.remove('is-invalid');
        const feedback = input.nextElementSibling;
        if (feedback && feedback.classList.contains('invalid-feedback')) {
            feedback.style.display = 'none';
        }
    }

    submitForm(form) {
        // Simulate form submission
        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;

        submitButton.disabled = true;
        submitButton.textContent = 'Enviando...';

        // Simulate API call
        setTimeout(() => {
            submitButton.disabled = false;
            submitButton.textContent = originalText;

            // Show success message
            const successDiv = document.createElement('div');
            successDiv.className = 'alert alert-success alert-dismissible fade show';
            successDiv.innerHTML = `
                <strong>¡Éxito!</strong> Tu mensaje ha sido enviado. Nos pondremos en contacto pronto.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;

            form.parentElement.insertBefore(successDiv, form);

            // Reset form
            form.reset();

            // Remove success message after 5 seconds
            setTimeout(() => {
                successDiv.remove();
            }, 5000);
        }, 1500);
    }
}

// ============================================
// LAZY IMAGE LOADING
// ============================================

class LazyImageLoader {
    constructor() {
        this.init();
    }

    init() {
        if (!('IntersectionObserver' in window)) {
            this.loadAllImages();
            return;
        }

        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    this.loadImage(entry.target);
                    imageObserver.unobserve(entry.target);
                }
            });
        });

        document.querySelectorAll('img[data-src]').forEach((img) => {
            imageObserver.observe(img);
        });
    }

    loadImage(img) {
        img.src = img.dataset.src;
        img.removeAttribute('data-src');
        img.classList.add('fade-in');
    }

    loadAllImages() {
        document.querySelectorAll('img[data-src]').forEach((img) => {
            this.loadImage(img);
        });
    }
}

// ============================================
// THEME SWITCHER (OPTIONAL)
// ============================================

class ThemeSwitcher {
    constructor() {
        this.init();
    }

    init() {
        this.loadSavedTheme();
    }

    loadSavedTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        this.applyTheme(savedTheme);
    }

    applyTheme(theme) {
        if (theme === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
        }
        localStorage.setItem('theme', theme);
    }

    toggle() {
        const currentTheme = localStorage.getItem('theme') || 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.applyTheme(newTheme);
    }
}

// ============================================
// PARALLAX EFFECT
// ============================================

class ParallaxEffect {
    constructor() {
        this.elements = document.querySelectorAll('[data-parallax]');
        this.init();
    }

    init() {
        if (this.elements.length > 0) {
            window.addEventListener(
                'scroll',
                throttle(() => this.updateParallax(), 50)
            );
        }
    }

    updateParallax() {
        const scrollPosition = window.pageYOffset;

        this.elements.forEach((element) => {
            const speed = element.dataset.parallax || 0.5;
            const yOffset = scrollPosition * speed;
            element.style.transform = `translateY(${yOffset}px)`;
        });
    }
}

// ============================================
// COUNTER ANIMATION (for stats)
// ============================================

class CounterAnimation {
    constructor() {
        this.init();
    }

    init() {
        if (!('IntersectionObserver' in window)) {
            this.animateAllCounters();
            return;
        }

        const counterObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    this.animateCounter(entry.target);
                    counterObserver.unobserve(entry.target);
                }
            });
        });

        document.querySelectorAll('[data-counter]').forEach((element) => {
            counterObserver.observe(element);
        });
    }

    animateCounter(element) {
        const finalValue = parseInt(element.dataset.counter) || 0;
        const duration = 2000;
        const steps = 60;
        const stepDuration = duration / steps;
        const increment = finalValue / steps;

        let currentValue = 0;
        const interval = setInterval(() => {
            currentValue += increment;
            if (currentValue >= finalValue) {
                currentValue = finalValue;
                clearInterval(interval);
            }
            element.textContent = Math.floor(currentValue) + '%';
        }, stepDuration);
    }

    animateAllCounters() {
        document.querySelectorAll('[data-counter]').forEach((element) => {
            this.animateCounter(element);
        });
    }
}

// ============================================
// MODAL ENHANCEMENTS
// ============================================

class ModalEnhancements {
    constructor() {
        this.init();
    }

    init() {
        document.querySelectorAll('.modal').forEach((modal) => {
            modal.addEventListener('show.bs.modal', (e) => this.handleModalShow(e));
            modal.addEventListener('hidden.bs.modal', (e) => this.handleModalHide(e));
        });
    }

    handleModalShow(e) {
        const modal = e.target;
        modal.style.animation = 'fadeIn 0.3s ease-out';
    }

    handleModalHide(e) {
        const modal = e.target;
        modal.style.animation = 'none';
    }
}

// ============================================
// KEYBOARD SHORTCUTS
// ============================================

class KeyboardShortcuts {
    constructor() {
        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => this.handleKeydown(e));
    }

    handleKeydown(e) {
        // Ctrl/Cmd + K to focus search (if search exists)
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('[data-search]');
            if (searchInput) {
                searchInput.focus();
            }
        }

        // Escape to close modals
        if (e.key === 'Escape') {
            const openModal = bootstrap.Modal.getInstance(document.querySelector('.modal.show'));
            if (openModal) {
                openModal.hide();
            }
        }

        // Alt + H for home
        if (e.altKey && e.key === 'h') {
            e.preventDefault();
            smoothScroll('#inicio');
        }
    }
}

// ============================================
// PAGE PERFORMANCE MONITOR
// ============================================

class PerformanceMonitor {
    constructor() {
        this.init();
    }

    init() {
        if (window.performance && window.performance.timing) {
            window.addEventListener('load', () => this.logPerformance());
        }
    }

    logPerformance() {
        const timing = window.performance.timing;
        const pageLoadTime = timing.loadEventEnd - timing.navigationStart;
        console.log(`Page Load Time: ${pageLoadTime}ms`);
    }
}

// ============================================
// INITIALIZE ALL MODULES
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing Agustina Falcon Application...');

    // Initialize core modules
    new NavbarScroll();
    new ScrollAnimations();
    new SmoothNavigation();
    new FormValidator();
    new LazyImageLoader();
    new ThemeSwitcher();
    new ParallaxEffect();
    new CounterAnimation();
    new ModalEnhancements();
    new KeyboardShortcuts();
    new PerformanceMonitor();

    console.log('✅ All modules initialized successfully');
});

// ============================================
// GLOBAL UTILITY FUNCTIONS
// ============================================

/**
 * Show toast notification
 * @param {String} message - Message to display
 * @param {String} type - Type: 'success', 'error', 'info', 'warning'
 */
window.showToast = function (message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed bottom-0 end-0 m-3`;
    toast.style.zIndex = '9999';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
};

/**
 * Get URL query parameters
 * @returns {Object} Query parameters
 */
window.getQueryParams = function () {
    const params = {};
    new URLSearchParams(window.location.search).forEach((value, key) => {
        params[key] = value;
    });
    return params;
};

/**
 * Copy text to clipboard
 * @param {String} text - Text to copy
 */
window.copyToClipboard = function (text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            window.showToast('Copiado al portapapeles', 'success');
        });
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        window.showToast('Copiado al portapapeles', 'success');
    }
};

/**
 * Detect browser and device type
 * @returns {Object} Browser and device info
 */
window.getDeviceInfo = function () {
    const ua = navigator.userAgent;
    return {
        isMobile: /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua),
        isTablet: /iPad|Android/i.test(ua) && !/Mobile/i.test(ua),
        isDesktop: !/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua),
        browser: ua,
    };
};

console.log('📱 Device Info:', window.getDeviceInfo());
