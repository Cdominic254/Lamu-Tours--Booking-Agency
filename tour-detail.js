(() => {
    const legacyIds = ['dhow', 'old-town', 'sandbank', 'fishing', 'cultural', 'water-sports', 'day-trips'];
    const requestedId = new URLSearchParams(location.search).get('id');
    const slug = /^\d+$/.test(requestedId || '')
        ? legacyIds[Number(requestedId) - 1]
        : requestedId;

    fetch('/api/catalogue')
        .then((response) => {
            if (!response.ok) throw new Error('Tours are temporarily unavailable.');
            return response.json();
        })
        .then(({ tours }) => {
            const tour = tours.find((item) => item.slug === slug);
            if (!tour) throw new Error('No tour matches the selected listing.');
            document.getElementById('tour-title').textContent = tour.name;
            document.getElementById('tour-desc').textContent = `Description: ${tour.description}`;
            document.getElementById('tour-duration').textContent = `Duration: ${tour.duration}`;
            const price = document.createElement('span');
            price.dataset.priceKes = tour.price;
            price.dataset.priceUnitEn = 'per person';
            price.dataset.priceUnitSw = 'kwa mtu';
            document.getElementById('tour-price').replaceChildren(document.createTextNode('Price: '), price);
            document.getElementById('tour-includes').hidden = true;
            document.getElementById('tour-itinerary').parentElement.hidden = true;
            document.getElementById('book-btn').href = `booking.html?tour=${encodeURIComponent(tour.slug)}`;

            const section = document.getElementById('tour-reviews');
            const details = document.createElement('details');
            const summary = document.createElement('summary');
            summary.textContent = 'Reviews and write a review';
            details.appendChild(summary);
            const list = document.createElement('div');
            list.className = 'review-list';
            details.appendChild(list);
            const form = document.createElement('form');
            form.className = 'catalogue-review-form';
            ['reviewer_name', 'reviewer_email', 'rating', 'comment'].forEach((name) => {
                const input = name === 'comment' ? document.createElement('textarea')
                    : name === 'rating' ? document.createElement('select')
                        : document.createElement('input');
                input.name = name;
                input.required = true;
                input.placeholder = name === 'reviewer_name' ? 'Your name'
                    : name === 'reviewer_email' ? 'Your email'
                        : name === 'comment' ? 'Share your experience' : '';
                if (name === 'reviewer_email') input.type = 'email';
                if (name === 'rating') {
                    const placeholder = document.createElement('option');
                    placeholder.value = '';
                    placeholder.textContent = 'Choose a rating';
                    input.appendChild(placeholder);
                    for (let value = 5; value >= 1; value -= 1) {
                        const option = document.createElement('option');
                        option.value = String(value);
                        option.textContent = `${value} stars`;
                        input.appendChild(option);
                    }
                }
                form.appendChild(input);
            });
            const status = document.createElement('p');
            status.setAttribute('role', 'status');
            const submit = document.createElement('button');
            submit.textContent = 'Publish review';
            form.appendChild(submit);
            details.append(form, status);
            section.appendChild(details);

            const reviewUrl = `/reviews?${new URLSearchParams({ target_type: 'tour', target_id: tour.slug })}`;
            const loadReviews = () => fetch(reviewUrl)
                .then((response) => response.json())
                .then(({ reviews }) => {
                    list.replaceChildren();
                    reviews.forEach((review) => {
                        const card = document.createElement('article');
                        card.className = 'review-card';
                        const title = document.createElement('strong');
                        title.textContent = `${'★'.repeat(review.rating)}${'☆'.repeat(5 - review.rating)} · ${review.reviewer_name}`;
                        const text = document.createElement('p');
                        text.textContent = review.comment;
                        card.append(title, text);
                        list.appendChild(card);
                    });
                    if (!reviews.length) list.textContent = 'No reviews yet. Be the first to share your experience.';
                });
            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const data = Object.fromEntries(new FormData(form));
                data.target_type = 'tour';
                data.target_id = tour.slug;
                try {
                    const response = await fetch('/review-submit', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                        body: JSON.stringify(data),
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || 'Review could not be published.');
                    form.reset();
                    status.textContent = 'Your review was published.';
                    await loadReviews();
                } catch (error) {
                    status.textContent = error.message;
                }
            });
            loadReviews().catch((error) => { list.textContent = error.message; });
        })
        .catch((error) => {
            document.getElementById('tour-title').textContent = 'Tour not found';
            document.getElementById('tour-desc').textContent = error.message;
            document.getElementById('book-btn').hidden = true;
        });
})();
