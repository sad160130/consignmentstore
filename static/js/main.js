// Main JavaScript functionality for the Consignment Store Directory

document.addEventListener('DOMContentLoaded', function() {
    // ===============================
    // Navigation & Dropdown Handling
    // ===============================
    const initNavigation = () => {
        const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
        const navMenu = document.querySelector('.nav-menu');
        const dropdowns = document.querySelectorAll('.dropdown');

        // Mobile menu toggle
        if (mobileMenuBtn && navMenu) {
            mobileMenuBtn.addEventListener('click', () => {
                navMenu.classList.toggle('active');
                mobileMenuBtn.setAttribute('aria-expanded', 
                    mobileMenuBtn.getAttribute('aria-expanded') === 'true' ? 'false' : 'true'
                );
            });
        }

        // Dropdown handling
        dropdowns.forEach(dropdown => {
            const toggle = dropdown.querySelector('.dropdown-toggle');
            const menu = dropdown.querySelector('.dropdown-menu');

            if (toggle && menu) {
                toggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    
                    // Close other dropdowns
                    dropdowns.forEach(d => {
                        if (d !== dropdown) {
                            d.querySelector('.dropdown-menu')?.classList.remove('active');
                            d.querySelector('.dropdown-toggle')?.setAttribute('aria-expanded', 'false');
                        }
                    });

                    // Toggle current dropdown
                    menu.classList.toggle('active');
                    toggle.setAttribute('aria-expanded', 
                        toggle.getAttribute('aria-expanded') === 'true' ? 'false' : 'true'
                    );
                });
            }
        });

        // Close dropdowns when clicking outside
        document.addEventListener('click', () => {
            dropdowns.forEach(dropdown => {
                dropdown.querySelector('.dropdown-menu')?.classList.remove('active');
                dropdown.querySelector('.dropdown-toggle')?.setAttribute('aria-expanded', 'false');
            });
        });
    };

    // ===============================
    // Search Functionality
    // ===============================
    const initSearch = () => {
        const searchForm = document.getElementById('searchForm');
        const searchInput = document.getElementById('searchInput');
        const searchResults = document.getElementById('searchResults');

        if (searchForm && searchInput) {
            let searchTimeout;

            searchInput.addEventListener('input', () => {
                clearTimeout(searchTimeout);
                
                if (searchInput.value.length >= 2) {
                    searchTimeout = setTimeout(() => {
                        searchForm.submit();
                    }, 500);
                }
            });
        }
    };

    // ===============================
    // Sorting and Filtering
    // ===============================
    const initSortingAndFiltering = () => {
        const sortButtons = document.querySelectorAll('.sort-btn');
        const filterInputs = document.querySelectorAll('.filter-input');
        
        // Sorting functionality
        sortButtons.forEach(button => {
            button.addEventListener('click', () => {
                const sortType = button.dataset.sort;
                const container = document.querySelector('.results-grid');
                
                if (container) {
                    const items = Array.from(container.children);
                    
                    items.sort((a, b) => {
                        const aValue = a.dataset[sortType];
                        const bValue = b.dataset[sortType];
                        
                        if (sortType === 'name') {
                            return aValue.localeCompare(bValue);
                        }
                        return parseInt(bValue) - parseInt(aValue);
                    });
                    
                    items.forEach(item => container.appendChild(item));
                    
                    // Update active state
                    sortButtons.forEach(btn => btn.classList.remove('active'));
                    button.classList.add('active');
                }
            });
        });

        // Filtering functionality
        filterInputs.forEach(input => {
            input.addEventListener('input', () => {
                const filterValue = input.value.toLowerCase();
                const items = document.querySelectorAll('.filterable-item');
                
                items.forEach(item => {
                    const text = item.textContent.toLowerCase();
                    item.style.display = text.includes(filterValue) ? '' : 'none';
                });
            });
        });
    };

    // ===============================
    // Animations
    // ===============================
    const initAnimations = () => {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '50px'
        });

        document.querySelectorAll('.fade-in').forEach(element => {
            observer.observe(element);
        });
    };

    // ===============================
    // Form Validation
    // ===============================
    const initFormValidation = () => {
        const forms = document.querySelectorAll('form[data-validate]');
        
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                let isValid = true;
                const requiredFields = form.querySelectorAll('[required]');
                
                requiredFields.forEach(field => {
                    if (!field.value.trim()) {
                        isValid = false;
                        field.classList.add('error');
                        
                        // Add error message
                        const errorMsg = field.nextElementSibling?.classList.contains('error-message') ?
                            field.nextElementSibling :
                            document.createElement('div');
                        
                        errorMsg.className = 'error-message';
                        errorMsg.textContent = `${field.getAttribute('data-label') || 'Field'} is required`;
                        
                        if (!field.nextElementSibling?.classList.contains('error-message')) {
                            field.parentNode.insertBefore(errorMsg, field.nextSibling);
                        }
                    } else {
                        field.classList.remove('error');
                        field.nextElementSibling?.classList.contains('error-message') &&
                            field.nextElementSibling.remove();
                    }
                });

                if (!isValid) {
                    e.preventDefault();
                }
            });
        });
    };

    // ===============================
    // Accessibility Enhancements
    // ===============================
    const initAccessibility = () => {
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                // Close all dropdowns
                document.querySelectorAll('.dropdown-menu.active').forEach(menu => {
                    menu.classList.remove('active');
                    menu.previousElementSibling?.setAttribute('aria-expanded', 'false');
                });
                
                // Close mobile menu
                document.querySelector('.nav-menu.active')?.classList.remove('active');
                document.querySelector('.mobile-menu-btn')?.setAttribute('aria-expanded', 'false');
            }
        });

        // Skip to main content
        const skipLink = document.createElement('a');
        skipLink.href = '#main';
        skipLink.className = 'skip-link';
        skipLink.textContent = 'Skip to main content';
        document.body.insertBefore(skipLink, document.body.firstChild);
    };

    // ===============================
    // Performance Optimizations
    // ===============================
    const initPerformance = () => {
        // Lazy load images
        const lazyImages = document.querySelectorAll('img[data-src]');
        
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });

        lazyImages.forEach(img => imageObserver.observe(img));

        // Debounce scroll events
        let scrollTimeout;
        window.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                // Handle scroll-based functionality
            }, 150);
        }, { passive: true });
    };

    // Initialize all functionality
    const init = () => {
        initNavigation();
        initSearch();
        initSortingAndFiltering();
        initAnimations();
        initFormValidation();
        initAccessibility();
        initPerformance();
    };

    // Start the application
    init();
});