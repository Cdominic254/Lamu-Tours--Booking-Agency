(() => {
    const currencyText = (amount) => `KSh ${Number(amount).toLocaleString()}`;

    function element(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function imageFor(url, alt) {
        if (!url || !/^(https?:\/\/|images\/|pictures\/)/i.test(url) || url.split('/').includes('..')) {
            return null;
        }
        const image = document.createElement('img');
        image.src = url;
        image.alt = alt;
        return image;
    }

    function appendReviewPanel(card, targetType, targetId) {
        const details = element('details', 'catalogue-reviews');
        const summary = element('summary', '', 'Reviews and write a review');
        const list = element('div', 'review-list');
        list.setAttribute('aria-live', 'polite');
        const form = document.createElement('form');
        form.className = 'catalogue-review-form';
        const name = document.createElement('input');
        name.name = 'reviewer_name';
        name.placeholder = 'Your name';
        name.required = true;
        const email = document.createElement('input');
        email.name = 'reviewer_email';
        email.type = 'email';
        email.placeholder = 'Your email';
        email.required = true;
        const rating = document.createElement('select');
        rating.name = 'rating';
        rating.required = true;
        const chooseRating = element('option', '', 'Choose a rating');
        chooseRating.value = '';
        rating.appendChild(chooseRating);
        ['5', '4', '3', '2', '1'].forEach((value) => {
            const option = element('option', '', `${value} - ${['', 'Needs improvement', 'Fair', 'Good', 'Very good', 'Excellent'][Number(value)]}`);
            option.value = value;
            rating.appendChild(option);
        });
        const comment = document.createElement('textarea');
        comment.name = 'comment';
        comment.placeholder = 'Share your experience';
        comment.required = true;
        const submit = element('button', '', 'Publish review');
        submit.type = 'submit';
        form.append(name, email, rating, comment, submit);
        const status = element('p', 'review-status');
        status.setAttribute('role', 'status');
        details.append(summary, list, status, form);
        card.appendChild(details);

        async function loadReviews() {
            try {
                const query = new URLSearchParams({ target_type: targetType, target_id: targetId });
                const response = await fetch(`/reviews?${query}`);
                if (!response.ok) throw new Error('Reviews could not be loaded.');
                const { reviews } = await response.json();
                list.replaceChildren();
                if (!reviews.length) {
                    list.appendChild(element('p', '', 'No reviews yet. Be the first to share your experience.'));
                    return;
                }
                reviews.forEach((review) => {
                    const reviewCard = element('article', 'review-card');
                    reviewCard.appendChild(element('strong', '', `${'★'.repeat(review.rating)}${'☆'.repeat(5 - review.rating)} · ${review.reviewer_name}`));
                    reviewCard.appendChild(element('p', '', review.comment));
                    list.appendChild(reviewCard);
                });
            } catch (error) {
                list.replaceChildren(element('p', '', error.message));
            }
        }

        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const data = Object.fromEntries(new FormData(form));
            data.target_type = targetType;
            data.target_id = targetId;
            try {
                const response = await fetch('/review-submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                    body: JSON.stringify(data),
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || 'Review could not be submitted.');
                form.reset();
                status.textContent = 'Your review was published.';
                await loadReviews();
            } catch (error) {
                status.textContent = error.message;
            }
        });
        loadReviews();
        return details;
    }

    function propertyCard(property) {
        const card = element('article', 'stay-card');
        card.dataset.location = property.location.toLowerCase();
        card.dataset.type = property.property_type.toLowerCase();
        card.dataset.guests = property.guests;
        card.dataset.price = property.price_per_night;
        const image = imageFor(property.image_url, property.name);
        if (image) card.appendChild(image);
        const content = element('div', 'stay-card-content');
        content.appendChild(element('h4', '', property.name));
        content.appendChild(element('p', 'stay-type', `${property.property_type} · ${property.location}`));
        const price = element('p', '');
        price.appendChild(document.createTextNode('From '));
        const amount = element('span', 'stay-price', currencyText(property.price_per_night));
        amount.dataset.priceKes = property.price_per_night;
        amount.dataset.priceUnitEn = 'per night';
        amount.dataset.priceUnitSw = 'kwa usiku';
        price.append(amount, document.createTextNode(' / night'));
        content.appendChild(price);
        const book = element('a', 'stay-card-link', 'Book this stay');
        book.href = `booking.html?stay=${encodeURIComponent(property.slug)}&guests=${property.guests}`;
        content.appendChild(book);
        card.appendChild(content);
        appendReviewPanel(card, 'property', property.slug);
        return card;
    }

    function tourCard(tour) {
        const card = element('article', 'tour');
        const image = imageFor(tour.image_url, tour.name);
        if (image) {
            image.className = 'tour-image';
            card.appendChild(image);
        }
        const content = element('div', 'tour-content');
        content.appendChild(element('h3', '', tour.name));
        content.appendChild(element('p', '', tour.description));
        const summary = element('p', '');
        summary.append(element('span', '', `Duration: ${tour.duration}`), document.createTextNode(' | Price: '));
        const amount = element('span', '', currencyText(tour.price));
        amount.dataset.priceKes = tour.price;
        amount.dataset.priceUnitEn = 'per person';
        amount.dataset.priceUnitSw = 'kwa mtu';
        summary.appendChild(amount);
        content.appendChild(summary);
        const actions = element('div', 'tour-actions');
        const details = element('a', 'details-button', 'View Details');
        details.href = `tour-details.html?id=${encodeURIComponent(tour.slug)}`;
        const book = element('a', 'book-button', 'Book Now');
        book.href = `booking.html?tour=${encodeURIComponent(tour.slug)}`;
        actions.append(details, book);
        content.appendChild(actions);
        card.appendChild(content);
        appendReviewPanel(card, 'tour', tour.slug);
        return card;
    }

    function renderDestinations(destinations) {
        const grid = document.querySelector('.destination-grid');
        if (!grid) return;
        grid.replaceChildren();
        destinations.forEach((destination) => {
            const card = element('article', 'destination-card');
            const image = imageFor(destination.image_url, destination.name);
            if (image) card.appendChild(image);
            const content = element('div', 'destination-card-content');
            content.appendChild(element('h3', '', destination.name));
            content.appendChild(element('p', '', destination.description));
            const link = element('a', 'destination-link', 'Find stays');
            link.href = '#stay-search-title';
            link.dataset.destination = destination.search_location;
            link.addEventListener('click', () => {
                const input = document.getElementById('stay-destination');
                const form = document.getElementById('stay-search-form');
                if (input && form) {
                    input.value = destination.search_location;
                    form.requestSubmit();
                }
            });
            content.appendChild(link);
            card.appendChild(content);
            grid.appendChild(card);
        });
    }

    function renderBookingOptions(tours, properties) {
        const select = document.querySelector('[data-catalogue-booking-select]');
        if (!select) return;
        const requested = new URLSearchParams(location.search).get('stay')
            || new URLSearchParams(location.search).get('tour')
            || '';
        const placeholder = select.options[0];
        select.replaceChildren(placeholder);
        const groups = [
            ['Tours', tours.map((tour) => ({
                slug: tour.slug, name: tour.name, price: tour.price, unit: 'per person', type: 'tour',
            }))],
            ['Stays', properties.map((property) => ({
                slug: property.slug, name: property.name, price: property.price_per_night, unit: 'per night', type: 'property',
            }))],
        ];
        groups.forEach(([label, items]) => {
            if (!items.length) return;
            const group = document.createElement('optgroup');
            group.label = label;
            items.forEach((item) => {
                const option = element('option', '', `${item.name} — ${currencyText(item.price)} ${item.unit}`);
                option.value = item.slug;
                option.dataset.priceKes = item.price;
                option.dataset.labelEn = item.name;
                option.dataset.labelSw = item.name;
                option.dataset.unitEn = item.unit;
                option.dataset.unitSw = item.unit === 'per night' ? 'kwa usiku' : 'kwa mtu';
                option.dataset.targetType = item.type;
                option.dataset.targetId = item.slug;
                group.appendChild(option);
            });
            select.appendChild(group);
        });
        select.value = requested;
        select.dispatchEvent(new Event('change', { bubbles: true }));

        let reviewPanel = document.getElementById('booking-item-reviews');
        if (!reviewPanel) {
            reviewPanel = element('div', '');
            reviewPanel.id = 'booking-item-reviews';
            select.after(reviewPanel);
        }
        function showSelectedReviews() {
            const item = select.selectedOptions[0];
            reviewPanel.replaceChildren();
            if (item?.dataset.targetType) {
                appendReviewPanel(reviewPanel, item.dataset.targetType, item.dataset.targetId);
            }
        }
        select.addEventListener('change', showSelectedReviews);
        showSelectedReviews();
    }

    fetch('/api/catalogue')
        .then((response) => {
            if (!response.ok) throw new Error('The catalog is temporarily unavailable.');
            return response.json();
        })
        .then(({ tours, properties, destinations }) => {
            const stayGrid = document.getElementById('stay-grid');
            if (stayGrid) {
                stayGrid.replaceChildren(...properties.map(propertyCard));
                window.dispatchEvent(new CustomEvent('lamu-properties-loaded'));
            }
            const tourGrid = document.getElementById('tour-list');
            if (tourGrid) {
                tourGrid.replaceChildren(...tours.map(tourCard));
            }
            renderDestinations(destinations);
            renderBookingOptions(tours, properties);
        })
        .catch((error) => {
            document.querySelectorAll('[data-catalogue-status]').forEach((node) => {
                node.textContent = error.message;
            });
        });
})();
