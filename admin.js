(() => {
    const csrfToken = document.querySelector('meta[name="admin-csrf"]').content;
    const message = document.getElementById('admin-message');

    function showMessage(text, isError = false) {
        message.textContent = text;
        message.classList.toggle('error', isError);
    }

    async function api(path, method = 'GET', data) {
        const response = await fetch(path, {
            method,
            headers: {
                'X-CSRF-Token': csrfToken,
                ...(data ? { 'Content-Type': 'application/json' } : {}),
            },
            ...(data ? { body: JSON.stringify(data) } : {}),
        });
        if (response.status === 204) return null;
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || 'Request failed.');
        return payload;
    }

    function addField(form, labelText, name, value, type = 'text', wide = false) {
        const label = document.createElement('label');
        label.textContent = labelText;
        if (wide) label.className = 'wide';
        const input = type === 'textarea' ? document.createElement('textarea') : document.createElement('input');
        if (type !== 'textarea') input.type = type;
        input.name = name;
        input.value = value ?? '';
        input.required = !['image_url'].includes(name);
        label.appendChild(input);
        form.appendChild(label);
    }

    function addRecordForm(container, title, item, fields, endpoint) {
        const card = document.createElement('article');
        card.className = 'admin-card';
        const heading = document.createElement('h3');
        heading.textContent = title;
        card.appendChild(heading);
        const form = document.createElement('form');
        form.className = 'record-form';
        fields.forEach(([label, key, type, wide]) => addField(form, label, key, item[key], type, wide));
        const save = document.createElement('button');
        save.type = 'submit';
        save.textContent = 'Save changes';
        form.appendChild(save);
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'danger';
        remove.textContent = 'Delete';
        form.appendChild(remove);
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const data = Object.fromEntries(new FormData(form));
            try {
                await api(endpoint, 'PUT', data);
                showMessage(`${title} updated.`);
                await loadCatalogue();
            } catch (error) {
                showMessage(error.message, true);
            }
        });
        remove.addEventListener('click', async () => {
            if (!window.confirm(`Delete ${title}?`)) return;
            try {
                await api(endpoint, 'DELETE');
                showMessage(`${title} deleted.`);
                await loadCatalogue();
            } catch (error) {
                showMessage(error.message, true);
            }
        });
        container.appendChild(card);
        card.appendChild(form);
    }

    const tourFields = [
        ['Name', 'name'], ['Price (KSh per guest)', 'price', 'number'],
        ['Duration', 'duration'], ['Image URL or images/ path', 'image_url'],
        ['Description', 'description', 'textarea', true],
    ];
    const propertyFields = [
        ['Name', 'name'], ['Type', 'property_type'], ['Location', 'location'],
        ['Price per night (KSh)', 'price_per_night', 'number'], ['Guest capacity', 'guests', 'number'],
        ['Image URL or images/ path', 'image_url'], ['Description', 'description', 'textarea', true],
    ];
    const destinationFields = [
        ['Name', 'name'], ['Search location', 'search_location'],
        ['Image URL or pictures/ path', 'image_url'], ['Description', 'description', 'textarea', true],
    ];

    async function loadCatalogue() {
        try {
            const data = await api('/api/admin/catalogue');
            const sections = [
                ['tour-records', data.tours, (item) => item.name, tourFields, (item) => `/api/admin/tours/${encodeURIComponent(item.slug)}`],
                ['property-records', data.properties, (item) => item.name, propertyFields, (item) => `/api/admin/properties/${item.id}`],
                ['destination-records', data.destinations, (item) => item.name, destinationFields, (item) => `/api/admin/destinations/${encodeURIComponent(item.slug)}`],
            ];
            sections.forEach(([id, items, title, fields, endpoint]) => {
                const container = document.getElementById(id);
                container.replaceChildren();
                items.forEach((item) => addRecordForm(container, title(item), item, fields, endpoint(item)));
            });
            const admins = document.getElementById('admin-records');
            admins.replaceChildren();
            data.admins.forEach((admin) => {
                const row = document.createElement('article');
                row.className = 'admin-card';
                const details = document.createElement('span');
                details.textContent = `${admin.name} · ${admin.email}`;
                row.appendChild(details);
                const remove = document.createElement('button');
                remove.type = 'button';
                remove.className = 'danger';
                remove.textContent = 'Remove admin';
                remove.addEventListener('click', async () => {
                    if (!window.confirm(`Remove admin account for ${admin.email}?`)) return;
                    try {
                        await api(`/api/admin/admins/${admin.id}`, 'DELETE');
                        showMessage('Admin account removed.');
                        await loadCatalogue();
                    } catch (error) {
                        showMessage(error.message, true);
                    }
                });
                row.appendChild(remove);
                admins.appendChild(row);
            });
        } catch (error) {
            showMessage(error.message, true);
        }
    }

    function bindCreateForm(id, endpoint, successMessage) {
        document.getElementById(id).addEventListener('submit', async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            try {
                await api(endpoint, 'POST', Object.fromEntries(new FormData(form)));
                form.reset();
                showMessage(successMessage);
                await loadCatalogue();
            } catch (error) {
                showMessage(error.message, true);
            }
        });
    }

    bindCreateForm('new-tour', '/api/admin/tours', 'Tour added.');
    bindCreateForm('new-property', '/api/admin/properties', 'Property added.');
    bindCreateForm('new-destination', '/api/admin/destinations', 'Destination added.');
    bindCreateForm('new-admin', '/api/admin/admins', 'Admin account created.');
    loadCatalogue();
})();
