(() => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const animatedElements = document.querySelectorAll('.tour, .destination-card, .stay-card, .listing, .attraction, .owner-listing, .review-card');

    if (reducedMotion || !('IntersectionObserver' in window)) return;

    document.documentElement.classList.add('motion-ready');
    animatedElements.forEach((element, index) => {
        element.classList.add('scroll-reveal');
        element.style.setProperty('--reveal-delay', `${Math.min(index % 6, 5) * 70}ms`);
    });

    const observer = new IntersectionObserver((entries, currentObserver) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add('is-visible');
            currentObserver.unobserve(entry.target);
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px' });

    animatedElements.forEach((element) => observer.observe(element));
})();
