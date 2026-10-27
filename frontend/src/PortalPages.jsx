import { useEffect, useState } from 'react';
import { getErrorMessage as messageFrom } from './utils.js';

async function apiRequest(path, { method = 'GET', data, csrfToken, signal } = {}) {
  const headers = { Accept: 'application/json' };
  if (data) headers['Content-Type'] = 'application/json';
  if (csrfToken) headers['X-CSRF-Token'] = csrfToken;
  const response = await fetch(path, {
    method,
    headers,
    ...(data ? { body: JSON.stringify(data) } : {}),
    ...(signal ? { signal } : {}),
  });
  if (response.status === 204) return null;
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (HTTP ${response.status}).`);
  return result;
}

function formatNumber(value) {
  const locale = document.documentElement.lang === 'sw' ? 'sw-KE' : 'en-KE';
  return Number(value).toLocaleString(locale);
}

function LanguageToggle() {
  const [language, setLanguage] = useState(document.documentElement.lang === 'sw' ? 'sw' : 'en');

  useEffect(() => {
    function syncLanguage(event) {
      setLanguage(event.detail.language);
    }

    document.addEventListener('lamu-language-changed', syncLanguage);
    return () => document.removeEventListener('lamu-language-changed', syncLanguage);
  }, []);

  function toggleLanguage() {
    const nextLanguage = language === 'en' ? 'sw' : 'en';
    window.setLamuLanguage?.(nextLanguage);
    setLanguage(nextLanguage);
  }

  return (
    <button
      className="rounded-full border border-[#dedbd2] px-4 py-2 text-sm font-semibold text-[#52615b] hover:bg-[#eeeee6]"
      type="button"
      data-language-toggle
      aria-label={language === 'en' ? 'Switch to Kiswahili' : 'Switch to English'}
      aria-pressed={language === 'sw'}
      onClick={toggleLanguage}
    >
      {language === 'en' ? 'Kiswahili' : 'English'}
    </button>
  );
}

function PortalCard({ children }) {
  return <main className="mx-auto max-w-3xl px-5 py-12 sm:px-8 sm:py-20"><div className="rounded-3xl border border-[#e9e5db] bg-white p-6 shadow-sm sm:p-10">{children}</div></main>;
}

function PortalIdentity({ children }) {
  return (
    <a className="brand-lockup flex items-center gap-3" href="/" aria-label={`Lamu Tours ${children}`}>
      <img className="brand-mark h-12 w-12" src="/logo.svg" alt="" />
      <span className="flex flex-col">
        <span className="brand-name text-xl font-bold text-[#203b35]">Lamu Tours</span>
        <span className="brand-tagline text-[0.6rem] font-bold uppercase tracking-[0.14em] text-[#52718a]">{children}</span>
      </span>
    </a>
  );
}

function PortalLogin({ role }) {
  const isVendor = role === 'vendor';
  const error = new URLSearchParams(window.location.search).get('error');
  return (
    <div className="min-h-screen bg-[#f8f7f2]">
      <header className="border-b border-[#e9e5db] bg-white px-5 py-4 sm:px-8"><div className="mx-auto flex max-w-7xl items-center justify-between gap-4"><PortalIdentity>{isVendor ? 'Vendor portal' : 'Admin portal'}</PortalIdentity><LanguageToggle /></div></header>
      <PortalCard>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#a75f3a]">{isVendor ? 'Vendor access' : 'Administration'}</p>
        <h1 className="display-font mt-3 text-4xl text-[#203b35]">{isVendor ? 'Welcome back to your island business.' : 'Welcome to your control room.'}</h1>
        <p className="mt-3 text-[#66736d]">{isVendor ? 'Your Lamu listings, departures, and guest bookings are all waiting here.' : 'Your Lamu marketplace overview, catalog, and account controls.'}</p>
        {error && <p className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}
        <form className="mt-7 space-y-5" action={isVendor ? '/vendor/login' : '/admin/login'} method="post">
          <label className="block"><span className="field-label">Email address</span><input className="field" name="email" type="email" autoComplete="username" required /></label>
          <label className="block"><span className="field-label">Password</span><input className="field" name="password" type="password" autoComplete="current-password" required /></label>
          <button className="min-h-12 w-full rounded-full bg-[#203b35] px-6 font-semibold text-white hover:bg-[#31554b]" type="submit">Sign in</button>
        </form>
        {isVendor ? (
          <p className="mt-6 text-sm text-[#66736d]">New vendor? <a className="font-semibold text-[#9a5534] hover:underline" href="/vendor/register">Create a vendor account</a></p>
        ) : (
          <p className="mt-6 text-sm text-[#66736d]">Traveler or vendor? <a className="font-semibold text-[#9a5534] hover:underline" href="/login.html">Use the traveler sign-in</a></p>
        )}
        <a className="mt-5 inline-block text-sm text-[#66736d] underline" href="/">Return to the public site</a>
      </PortalCard>
    </div>
  );
}

export function AdminLoginPage() {
  return <PortalLogin role="admin" />;
}

export function VendorLoginPage() {
  return <PortalLogin role="vendor" />;
}

export function VendorRegistrationPage() {
  const [csrfToken, setCsrfToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    apiRequest('/api/vendor/registration-token', { signal: controller.signal })
      .then(({ csrf_token: token }) => setCsrfToken(token))
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(messageFrom(requestError));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  async function submitRegistration(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      await apiRequest('/vendor/register', {
        method: 'POST',
        data,
        csrfToken,
      });
      window.location.assign('/vendor/dashboard');
    } catch (requestError) {
      setError(messageFrom(requestError));
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f8f7f2]">
      <header className="border-b border-[#e9e5db] bg-white px-5 py-4 sm:px-8"><div className="mx-auto flex max-w-7xl items-center justify-between gap-4"><PortalIdentity>Vendor portal</PortalIdentity><LanguageToggle /></div></header>
      <PortalCard>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#a75f3a]">Partner with us</p>
        <h1 className="display-font mt-3 text-4xl text-[#203b35]">Bring your Lamu experience to more travelers.</h1>
        <p className="mt-3 text-[#66736d]">Bring your local knowledge to more travelers. Create an account to publish experiences, set departures, and keep your bookings in view.</p>
        {error && <p className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}
        <form className="mt-7 space-y-5" onSubmit={submitRegistration}>
          <label className="block"><span className="field-label">Your name or business name</span><input className="field" name="name" autoComplete="name" required /></label>
          <label className="block"><span className="field-label">Email address</span><input className="field" name="email" type="email" autoComplete="email" required /></label>
          <label className="block"><span className="field-label">Password</span><input className="field" name="password" type="password" minLength="12" autoComplete="new-password" required /><span className="mt-1 block text-xs text-[#7a857f]">Use at least 12 characters.</span></label>
          <button className="min-h-12 w-full rounded-full bg-[#b96e45] px-6 font-semibold text-white hover:bg-[#a45d38] disabled:opacity-60" type="submit" disabled={loading || submitting || !csrfToken}>
            {loading ? 'Preparing secure sign-up…' : submitting ? 'Creating account…' : 'Create vendor account'}
          </button>
        </form>
        <p className="mt-6 text-sm text-[#66736d]">Already registered? <a className="font-semibold text-[#9a5534] hover:underline" href="/vendor/login">Vendor sign in</a></p>
        <a className="mt-5 inline-block text-sm text-[#66736d] underline" href="/">Return to the public site</a>
      </PortalCard>
    </div>
  );
}

function PortalHeader({ role, actor, onSignOut }) {
  return (
    <header className="portal-header bg-[#203b35] text-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-8">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#f1b28b]">{role} portal</p>
          <h1 className="display-font mt-1 text-3xl">{actor}</h1>
        </div>
        <div className="flex items-center gap-3">
          <LanguageToggle />
          <a className="rounded-full border border-white/30 px-4 py-2 text-sm font-semibold text-white hover:bg-white/10" href="/">Public site</a>
          {onSignOut && <button className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-[#203b35] hover:bg-[#e8eee9]" type="button" onClick={onSignOut}>Sign out</button>}
        </div>
      </div>
    </header>
  );
}

function Notice({ children, error = false }) {
  if (!children) return null;
  return <p className={`rounded-xl p-4 text-sm ${error ? 'bg-red-50 text-red-800' : 'bg-green-50 text-green-800'}`} role={error ? 'alert' : 'status'}>{children}</p>;
}

const tourFields = [
  { name: 'name', label: 'Name', required: true },
  { name: 'category', label: 'Category', required: true },
  { name: 'price', label: 'Price (KSh per guest)', type: 'number', min: 1, required: true },
  { name: 'duration', label: 'Duration', required: true },
  { name: 'pickup_point', label: 'Pickup point', required: true },
  { name: 'min_group_size', label: 'Minimum group size', type: 'number', min: 1, required: true },
  { name: 'max_group_size', label: 'Maximum group size', type: 'number', min: 1, required: true },
  { name: 'image_url', label: 'Image URL or images/ path' },
  { name: 'itinerary', label: 'Itinerary (one step per line)', type: 'textarea', wide: true },
  { name: 'inclusions', label: 'Inclusions (one per line)', type: 'textarea', wide: true },
  { name: 'exclusions', label: 'Exclusions (one per line)', type: 'textarea', wide: true },
  { name: 'description', label: 'Description', type: 'textarea', wide: true, required: true },
];

const propertyFields = [
  { name: 'name', label: 'Name', required: true },
  { name: 'property_type', label: 'Type', type: 'select', options: ['hotel', 'home', 'guest house', 'villa'], required: true },
  { name: 'location', label: 'Location', required: true },
  { name: 'price_per_night', label: 'Price per night (KSh)', type: 'number', min: 1, required: true },
  { name: 'guests', label: 'Guest capacity', type: 'number', min: 1, required: true },
  { name: 'image_url', label: 'Image URL or images/ path' },
  { name: 'description', label: 'Description', type: 'textarea', wide: true, required: true },
];

const destinationFields = [
  { name: 'name', label: 'Name', required: true },
  { name: 'search_location', label: 'Search location', required: true },
  { name: 'image_url', label: 'Image URL or pictures/ path' },
  { name: 'description', label: 'Description', type: 'textarea', wide: true, required: true },
];

function DashboardField({ field, value }) {
  const common = {
    className: 'field',
    name: field.name,
    required: Boolean(field.required),
    ...(field.min ? { min: field.min } : {}),
    ...(field.type === 'number' ? { step: '1' } : {}),
  };
  return (
    <label className={field.wide ? 'block sm:col-span-2' : 'block'}>
      <span className="field-label">{field.label}</span>
      {field.type === 'textarea'
        ? <textarea {...common} className="field min-h-24 resize-y" defaultValue={Array.isArray(value) ? value.join('\n') : value ?? ''} />
        : field.type === 'select'
          ? <select {...common} defaultValue={value ?? field.options[0]}>{field.options.map((option) => <option key={option} value={option}>{option}</option>)}</select>
          : <input {...common} type={field.type || 'text'} minLength={field.minLength} defaultValue={value ?? ''} />}
    </label>
  );
}

function DataForm({ fields, item = {}, submitLabel, onSubmit, children }) {
  return (
    <form
      className="grid gap-4 sm:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(Object.fromEntries(new FormData(event.currentTarget)), event.currentTarget);
      }}
    >
      {fields.map((field) => <DashboardField field={field} key={field.name} value={item[field.name]} />)}
      <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
        <button className="rounded-full bg-[#203b35] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#31554b] disabled:opacity-60" type="submit">{submitLabel}</button>
        {children}
      </div>
    </form>
  );
}

function SectionCard({ title, description, children }) {
  return (
    <section className="rounded-2xl border border-[#e9e5db] bg-white p-5 shadow-sm sm:p-7">
      <div className="mb-5">
        <h2 className="display-font text-2xl text-[#203b35]">{title}</h2>
        {description && <p className="mt-2 text-sm leading-6 text-[#66736d]">{description}</p>}
      </div>
      {children}
    </section>
  );
}

function CatalogSection({ title, items, fields, basePath, onMutation, ownerLabel, csrfToken }) {
  const [formError, setFormError] = useState('');
  const itemLabel = title.endsWith('ies') ? `${title.slice(0, -3)}y` : title.slice(0, -1);
  const uploadEndpoint = basePath.startsWith('/api/vendor') ? '/api/vendor/uploads' : '/api/admin/uploads';

  function ImageUpload() {
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');

    async function upload(event) {
      const input = event.currentTarget;
      const file = input.files?.[0];
      const form = input.form;
      if (!file || !form) return;
      setUploading(true);
      setError('');
      const body = new FormData();
      body.append('image', file);
      try {
        const response = await fetch(uploadEndpoint, {
          method: 'POST',
          headers: { Accept: 'application/json', 'X-CSRF-Token': csrfToken || '' },
          body,
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Photo upload failed.');
        const imageField = form.elements.namedItem('image_url');
        if (imageField) imageField.value = result.image_url;
      } catch (uploadError) {
        setError(messageFrom(uploadError));
      } finally {
        setUploading(false);
        input.value = '';
      }
    }

    return (
      <label className="block">
        <span className="field-label">Upload a photo</span>
        <input className="field" type="file" accept="image/jpeg,image/png,image/webp" onChange={upload} disabled={uploading} />
        {uploading && <span className="mt-1 block text-xs text-[#66736d]">Uploading photo…</span>}
        {error && <span className="mt-1 block text-xs text-red-700" role="alert">{error}</span>}
      </label>
    );
  }

  async function create(data, form) {
    setFormError('');
    const success = await onMutation(basePath, 'POST', data, `${itemLabel} added.`);
    if (success) form.reset();
    else setFormError('The new listing could not be saved.');
  }

  async function update(url, data) {
    setFormError('');
    const success = await onMutation(url, 'PUT', data, 'Changes saved.');
    if (!success) setFormError('Changes could not be saved.');
  }

  async function remove(url, name) {
    if (!window.confirm(`Delete ${name}? This cannot be undone.`)) return;
    setFormError('');
    const success = await onMutation(url, 'DELETE', undefined, 'Listing deleted.');
    if (!success) setFormError('This listing could not be deleted.');
  }

  return (
    <SectionCard title={title} description={`Create and manage ${title.toLowerCase()}.`}>
      <DataForm fields={fields} submitLabel={`Add ${itemLabel.toLowerCase()}`} onSubmit={create}>
        {fields.some((field) => field.name === 'image_url') && <ImageUpload />}
      </DataForm>
      <Notice error>{formError}</Notice>
      <div className="mt-6 space-y-4">
        {items.length === 0 && <p className="rounded-xl bg-[#f5f3ed] p-4 text-sm text-[#66736d]">No {title.toLowerCase()} yet.</p>}
        {items.map((item) => {
          const url = `${basePath}/${encodeURIComponent(item.slug ?? item.id)}`;
          return (
            <article className="rounded-xl border border-[#e9e5db] p-4 sm:p-5" key={`${item.id ?? item.slug}-${JSON.stringify(item)}`}>
              <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-[#203b35]">{item.name}</h3>
                  {ownerLabel?.(item) && <p className="mt-1 text-xs text-[#66736d]">{ownerLabel(item)}</p>}
                </div>
                {item.price != null && <span className="text-sm font-semibold text-[#9a5534]">KSh {formatNumber(item.price)}</span>}
                {item.price_per_night != null && <span className="text-sm font-semibold text-[#9a5534]">KSh {formatNumber(item.price_per_night)} / night</span>}
              </div>
              <DataForm fields={fields} item={item} submitLabel="Save changes" onSubmit={(data) => update(url, data)}>
                {fields.some((field) => field.name === 'image_url') && <ImageUpload />}
                <button
                  className="rounded-full border border-red-200 px-5 py-2.5 text-sm font-semibold text-red-700 hover:bg-red-50"
                  type="button"
                  onClick={() => remove(url, item.name)}
                >
                  Delete
                </button>
              </DataForm>
            </article>
          );
        })}
      </div>
    </SectionCard>
  );
}

function VendorBookingsSection({ csrfToken }) {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const transitions = {
    requested: ['confirmed', 'cancelled'],
    confirmed: ['in_preparation', 'cancelled'],
    in_preparation: ['completed', 'cancelled'],
    completed: [],
    cancelled: [],
  };

  async function load() {
    setLoading(true);
    setError('');
    try {
      const result = await apiRequest('/api/vendor/bookings');
      setBookings(result.bookings);
    } catch (loadError) {
      setError(messageFrom(loadError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function updateStatus(booking, status) {
    if (status === 'cancelled' && !window.confirm(`Cancel booking #${booking.id}? Availability will be released.`)) return;
    setError('');
    setMessage('');
    try {
      const result = await apiRequest(`/api/vendor/bookings/${booking.id}/status`, {
        method: 'POST',
        data: { status },
        csrfToken,
      });
      await load();
      setMessage(result.email_sent ? `Booking #${booking.id} updated and customer emailed.` : `Booking #${booking.id} updated; customer email could not be delivered.`);
    } catch (updateError) {
      setError(messageFrom(updateError));
    }
  }

  return (
    <SectionCard title="Bookings" description="View reservations for your tours and progress them through the service workflow.">
      <Notice error>{error}</Notice><Notice>{message}</Notice>
      {loading && <p className="text-sm text-[#66736d]" role="status">Loading bookings…</p>}
      {!loading && bookings.length === 0 && <p className="rounded-xl bg-[#f5f3ed] p-4 text-sm text-[#66736d]">No tour bookings yet.</p>}
      <div className="space-y-4">
        {bookings.map((booking) => (
          <article className="rounded-xl border border-[#e9e5db] p-4 sm:p-5" key={booking.id}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div><h3 className="font-semibold capitalize text-[#203b35]">{booking.tour_name}</h3><p className="mt-1 text-sm text-[#66736d]">Booking #{booking.id} · {booking.date} at {booking.time} · {booking.guests} guest{booking.guests === 1 ? '' : 's'}</p><p className="mt-1 text-sm text-[#66736d]">{booking.name} · {booking.email} · {booking.phone}</p></div>
              <span className="rounded-full bg-[#efeee7] px-3 py-1 text-sm font-semibold capitalize text-[#52615b]">{booking.status.replaceAll('_', ' ')}</span>
            </div>
            <p className="mt-2 text-xs text-[#7a857f]">KSh {formatNumber(booking.amount)} · Payment: {booking.payment_status}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {(transitions[booking.status] || []).map((status) => (
                <button className={`rounded-full px-4 py-2 text-sm font-semibold ${status === 'cancelled' ? 'border border-red-200 text-red-700' : 'bg-[#203b35] text-white hover:bg-[#31554b]'}`} key={status} type="button" onClick={() => updateStatus(booking, status)}>
                  Mark {status.replaceAll('_', ' ')}
                </button>
              ))}
            </div>
          </article>
        ))}
      </div>
    </SectionCard>
  );
}

function AdminAccounts({ admins, vendors, onMutation }) {
  const [error, setError] = useState('');

  async function addAdmin(data, form) {
    const success = await onMutation('/api/admin/admins', 'POST', data, 'Admin account created.');
    if (success) form.reset();
    else setError('Admin account could not be created.');
  }

  async function deleteAdmin(admin) {
    if (!window.confirm(`Remove the admin account for ${admin.email}?`)) return;
    const success = await onMutation(`/api/admin/admins/${admin.id}`, 'DELETE', undefined, 'Admin account removed.');
    if (!success) setError('Admin account could not be removed.');
  }

  async function deleteVendor(vendor) {
    if (!window.confirm(`Remove ${vendor.name} and all of their tours and properties?`)) return;
    const success = await onMutation(`/api/admin/vendors/${vendor.id}`, 'DELETE', undefined, 'Vendor account and listings removed.');
    if (!success) setError('Vendor account could not be removed.');
  }

  return (
    <SectionCard title="Accounts" description="Manage staff access and self-registered vendor accounts.">
      <h3 className="mb-3 font-semibold text-[#203b35]">Create an admin account</h3>
      <DataForm
        fields={[
          { name: 'name', label: 'Name', required: true },
          { name: 'email', label: 'Email', type: 'email', required: true },
          { name: 'password', label: 'Password (at least 12 characters)', type: 'password', minLength: 12, required: true },
        ]}
        submitLabel="Create admin"
        onSubmit={addAdmin}
      />
      <Notice error>{error}</Notice>
      <div className="mt-7 grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 font-semibold text-[#203b35]">Admin accounts</h3>
          <div className="space-y-3">
            {admins.map((admin) => (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-[#f5f3ed] p-4" key={admin.id}>
                <span className="text-sm text-[#52615b]">{admin.name} · {admin.email}</span>
                <button className="text-sm font-semibold text-red-700 hover:underline" type="button" onClick={() => deleteAdmin(admin)}>Remove</button>
              </div>
            ))}
          </div>
        </div>
        <div>
          <h3 className="mb-3 font-semibold text-[#203b35]">Vendor accounts</h3>
          <div className="space-y-3">
            {vendors.length === 0 && <p className="rounded-xl bg-[#f5f3ed] p-4 text-sm text-[#66736d]">No vendors have registered yet.</p>}
            {vendors.map((vendor) => (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-[#f5f3ed] p-4" key={vendor.id}>
                <span className="text-sm text-[#52615b]">
                  <strong className="block text-[#203b35]">{vendor.name}</strong>
                  {vendor.email}<span className="mt-1 block text-xs">{vendor.tour_count} tours · {vendor.property_count} properties</span>
                </span>
                <button className="text-sm font-semibold text-red-700 hover:underline" type="button" onClick={() => deleteVendor(vendor)}>Remove vendor</button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </SectionCard>
  );
}

function usePortalData(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      setData(await apiRequest(path));
    } catch (loadError) {
      setError(messageFrom(loadError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [path]);

  async function mutate(url, method, payload, successMessage) {
    if (!data?.csrf_token) {
      setError('Your session has expired. Sign in again to continue.');
      return false;
    }
    setError('');
    setMessage('');
    try {
      await apiRequest(url, { method, data: payload, csrfToken: data.csrf_token });
      setMessage(successMessage);
      await load();
      return true;
    } catch (mutationError) {
      setError(messageFrom(mutationError));
      return false;
    }
  }

  return { data, loading, error, message, load, mutate };
}

function makeSignOut({ endpoint, csrfToken, redirectTo, onError }) {
  async function signOut() {
    try {
      await apiRequest(endpoint, { method: 'POST', csrfToken });
      window.location.assign(redirectTo);
    } catch (error) {
      onError(messageFrom(error));
    }
  }
  return signOut;
}

function DashboardLayout({ role, actor, signOut, children }) {
  return (
    <div className="min-h-screen bg-[#f8f7f2]">
      <PortalHeader role={role} actor={actor} onSignOut={signOut} />
      <main className="mx-auto max-w-7xl space-y-6 px-5 py-8 sm:px-8 sm:py-10">{children}</main>
    </div>
  );
}

function DashboardStatus({ error, message }) {
  return <><Notice error>{error}</Notice><Notice>{message}</Notice></>;
}

function AvailabilitySection({ tours, endpoint, csrfToken }) {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const result = await apiRequest(endpoint);
      setSchedules(result.schedules);
    } catch (loadError) {
      setError(messageFrom(loadError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [endpoint]);

  async function save(event) {
    event.preventDefault();
    const form = event.currentTarget;
    setError('');
    setMessage('');
    const data = Object.fromEntries(new FormData(form));
    try {
      await apiRequest(endpoint, { method: 'POST', data, csrfToken });
      form.reset();
      await load();
      setMessage('Departure published.');
    } catch (saveError) {
      setError(messageFrom(saveError));
    }
  }

  async function remove(schedule) {
    if (!window.confirm('Remove this departure?')) return;
    setError('');
    try {
      await apiRequest(`${endpoint}/${schedule.id}`, { method: 'DELETE', csrfToken });
      await load();
      setMessage('Departure removed.');
    } catch (removeError) {
      setError(messageFrom(removeError));
    }
  }

  async function update(schedule, event) {
    event.preventDefault();
    const form = event.currentTarget;
    setError('');
    setMessage('');
    try {
      await apiRequest(`${endpoint}/${schedule.id}`, {
        method: 'PUT',
        data: Object.fromEntries(new FormData(form)),
        csrfToken,
      });
      await load();
      setMessage('Departure updated.');
    } catch (updateError) {
      setError(messageFrom(updateError));
    }
  }

  return (
    <SectionCard title="Tour availability" description="Publish departure dates and times with a guest capacity. Only future departures with remaining spaces can be booked.">
      <Notice error>{error}</Notice><Notice>{message}</Notice>
      <form className="grid gap-4 sm:grid-cols-3" onSubmit={save}>
        <label><span className="field-label">Tour</span><select className="field" name="tour_slug" required defaultValue=""><option value="" disabled>Choose a tour</option>{tours.map((tour) => <option value={tour.slug} key={tour.slug}>{tour.name}</option>)}</select></label>
        <label><span className="field-label">Departure date and time (Lamu time)</span><input className="field" type="datetime-local" name="starts_at" required /></label>
        <label><span className="field-label">Guest capacity</span><input className="field" type="number" min="1" name="capacity" required /></label>
        <button className="rounded-full bg-[#203b35] px-5 py-2.5 text-sm font-semibold text-white sm:col-span-3 sm:justify-self-start" type="submit" disabled={!tours.length}>Add departure</button>
      </form>
      {loading && <p className="mt-5 text-sm text-[#66736d]" role="status">Loading departures…</p>}
      {!loading && schedules.length === 0 && <p className="mt-5 rounded-xl bg-[#f5f3ed] p-4 text-sm text-[#66736d]">No departures published yet.</p>}
      <div className="mt-5 space-y-3">
        {schedules.map((schedule) => (
          <div className="rounded-xl border border-[#e9e5db] p-4" key={schedule.id}>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div><p className="font-semibold text-[#203b35]">{tours.find((tour) => tour.slug === schedule.tour_slug)?.name || schedule.tour_slug}</p><p className="mt-1 text-sm text-[#66736d]">{schedule.booked_count}/{schedule.capacity} guests booked</p></div>
              <button className="text-sm font-semibold text-red-700 hover:underline" type="button" onClick={() => remove(schedule)}>Remove</button>
            </div>
            <form className="grid gap-3 sm:grid-cols-[1fr_10rem_auto]" onSubmit={(event) => update(schedule, event)}>
              <label><span className="field-label">Departure (Lamu time)</span><input className="field" type="datetime-local" name="starts_at" defaultValue={schedule.starts_at} required /></label>
              <label><span className="field-label">Capacity</span><input className="field" type="number" name="capacity" min={schedule.booked_count} defaultValue={schedule.capacity} required /></label>
              <button className="self-end rounded-full border border-[#203b35] px-4 py-3 text-sm font-semibold text-[#203b35]" type="submit">Update</button>
            </form>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

function DashboardLoadError({ role, error, onRetry }) {
  const loginUrl = role.toLowerCase() === 'admin' ? '/admin/login' : '/vendor/login';
  return (
    <div className="min-h-screen bg-[#f8f7f2]">
      <PortalHeader role={role} actor="Dashboard unavailable" />
      <main className="mx-auto max-w-3xl px-5 py-12 sm:px-8">
        <div className="rounded-2xl border border-red-200 bg-white p-6">
          <Notice error>{error}</Notice>
          <div className="mt-5 flex gap-4">
            <button className="font-semibold text-[#203b35] underline" type="button" onClick={onRetry}>Try again</button>
            <a className="font-semibold text-[#9a5534] underline" href={loginUrl}>Sign in</a>
          </div>
        </div>
      </main>
    </div>
  );
}

function displayTimestamp(value) {
  if (!value) return '—';
  const date = new Date(value);
  const locale = document.documentElement.lang === 'sw' ? 'sw-KE' : 'en-KE';
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString(locale);
}

function AdminUserManagement({ customers, vendors, onMutation }) {
  const accounts = [
    ...customers.map((user) => ({ ...user, role: 'customer' })),
    ...vendors.map((user) => ({ ...user, role: 'vendor' })),
  ];

  return (
    <SectionCard title="User management" description="Review customer and operator accounts, and suspend or restore access without deleting booking history.">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-left text-sm">
          <thead><tr className="border-b border-[#e9e5db] text-[#66736d]">{['Name', 'Email', 'Role', 'Bookings', 'Access'].map((label) => <th className="px-3 py-3 font-semibold" key={label}>{label}</th>)}</tr></thead>
          <tbody>{accounts.map((account) => (
            <tr className="border-b border-[#f0ede6] text-[#52615b]" key={`${account.role}-${account.id}`}>
              <td className="px-3 py-3">{account.name}</td>
              <td className="px-3 py-3">{account.email}</td>
              <td className="px-3 py-3 capitalize">{account.role}</td>
              <td className="px-3 py-3">{account.booking_count ?? '—'}</td>
              <td className="px-3 py-3">
                <button
                  className={`font-semibold hover:underline ${account.is_active ? 'text-red-700' : 'text-[#26734d]'}`}
                  type="button"
                  onClick={() => onMutation(
                    `/api/admin/users/${account.role}/${account.id}/status`,
                    'POST',
                    { active: !account.is_active },
                    `${account.role === 'vendor' ? 'Vendor' : 'Customer'} access ${account.is_active ? 'suspended' : 'restored'}.`,
                  )}
                >
                  {account.is_active ? 'Suspend access' : 'Restore access'}
                </button>
              </td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      {accounts.length === 0 && <p className="rounded-xl bg-[#f5f3ed] p-4 text-sm text-[#66736d]">No customer or vendor accounts yet.</p>}
    </SectionCard>
  );
}

function AdminBookingCard({ booking, onMutation }) {
  const [reason, setReason] = useState('');
  const [refundStatus, setRefundStatus] = useState('');
  const refundNext = {
    none: ['pending_review'],
    pending_review: ['approved', 'rejected'],
    approved: ['completed'],
    rejected: ['pending_review'],
    completed: [],
  }[booking.refund_status] || [];

  async function openDispute(event) {
    event.preventDefault();
    const success = await onMutation(
      `/api/admin/bookings/${booking.id}/disputes`,
      'POST',
      { reason },
      `Dispute opened for booking #${booking.id}.`,
    );
    if (success) setReason('');
  }

  async function updateRefund(status) {
    if (status === 'completed' && !window.confirm('Confirm the refund was manually issued outside this app?')) {
      setRefundStatus('');
      return;
    }
    await onMutation(
      `/api/admin/bookings/${booking.id}/refund`,
      'POST',
      { status },
      `Refund status for booking #${booking.id} updated.`,
    );
    setRefundStatus('');
  }

  return (
    <article className="rounded-xl border border-[#e9e5db] p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-[#203b35]">#{booking.id} · {booking.tour_name}</h3>
          <p className="mt-1 text-sm text-[#66736d]">{booking.name} · {booking.email} · {booking.phone}</p>
          <p className="mt-1 text-sm text-[#66736d]">{booking.date} at {booking.time} · {booking.guests} guest{booking.guests === 1 ? '' : 's'}</p>
        </div>
        <span className="rounded-full bg-[#efeee7] px-3 py-1 text-sm font-semibold capitalize text-[#52615b]">{booking.status.replaceAll('_', ' ')}</span>
      </div>
      <p className="mt-3 text-sm text-[#52615b]">KSh {formatNumber(booking.amount)} · Payment: {booking.payment_status} · Refund: {booking.refund_status.replaceAll('_', ' ')}</p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        {['requested', 'confirmed', 'in_preparation'].includes(booking.status) && (
          <button
            className="rounded-full border border-red-200 px-4 py-2 text-sm font-semibold text-red-700"
            type="button"
            onClick={() => {
              if (window.confirm(`Cancel booking #${booking.id}? Reserved availability will be released.`)) {
                onMutation(`/api/admin/bookings/${booking.id}/cancel`, 'POST', {}, `Booking #${booking.id} cancelled.`);
              }
            }}
          >Cancel booking</button>
        )}
        {booking.payment_status === 'paid' && refundNext.length > 0 && (
          <label className="flex items-center gap-2 text-sm text-[#52615b]">
            <span>Refund review</span>
            <select
              className="rounded-lg border border-[#dcd8cd] bg-white px-3 py-2"
              value={refundStatus}
              onChange={(event) => {
                const status = event.target.value;
                setRefundStatus(status);
                if (status) updateRefund(status);
              }}
            >
              <option value="">Choose action</option>
              {refundNext.map((status) => <option value={status} key={status}>{status.replaceAll('_', ' ')}</option>)}
            </select>
          </label>
        )}
      </div>
      <form className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto]" onSubmit={openDispute}>
        <label><span className="field-label">Open dispute / internal case</span><textarea className="field min-h-20" value={reason} onChange={(event) => setReason(event.target.value)} minLength={10} maxLength={3000} placeholder="Summarize the customer or vendor concern…" required /></label>
        <button className="self-end rounded-full border border-[#203b35] px-4 py-3 text-sm font-semibold text-[#203b35]" type="submit">Open case</button>
      </form>
    </article>
  );
}

function AdminDisputes({ disputes, onMutation }) {
  const [resolutions, setResolutions] = useState({});
  return (
    <SectionCard title="Dispute handling" description="Create internal cases from a booking and record the resolution for the audit trail.">
      {disputes.length === 0 && <p className="rounded-xl bg-[#f5f3ed] p-4 text-sm text-[#66736d]">No dispute cases have been recorded.</p>}
      <div className="space-y-3">
        {disputes.map((dispute) => (
          <article className="rounded-xl border border-[#e9e5db] p-4" key={dispute.id}>
            <div className="flex flex-wrap justify-between gap-2">
              <h3 className="font-semibold text-[#203b35]">Case #{dispute.id} · Booking #{dispute.booking_id} · {dispute.tour}</h3>
              <span className="text-sm font-semibold capitalize text-[#66736d]">{dispute.status}</span>
            </div>
            <p className="mt-2 text-sm text-[#52615b]">{dispute.booking_name} · {dispute.booking_email}</p>
            <p className="mt-2 whitespace-pre-wrap text-sm text-[#52615b]">{dispute.reason}</p>
            {dispute.status === 'open'
              ? <form className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto]" onSubmit={async (event) => {
                event.preventDefault();
                const resolution = resolutions[dispute.id] || '';
                const success = await onMutation(`/api/admin/disputes/${dispute.id}`, 'PUT', { resolution }, `Dispute #${dispute.id} resolved.`);
                if (success) setResolutions((current) => ({ ...current, [dispute.id]: '' }));
              }}>
                <label><span className="field-label">Resolution</span><textarea className="field min-h-20" minLength={10} maxLength={3000} required value={resolutions[dispute.id] || ''} onChange={(event) => setResolutions((current) => ({ ...current, [dispute.id]: event.target.value }))} /></label>
                <button className="self-end rounded-full bg-[#203b35] px-4 py-3 text-sm font-semibold text-white" type="submit">Resolve case</button>
              </form>
              : <p className="mt-3 whitespace-pre-wrap text-sm text-[#52615b]"><strong>Resolution:</strong> {dispute.resolution}</p>}
          </article>
        ))}
      </div>
    </SectionCard>
  );
}

function AdminOperationsSection() {
  const { data, loading, error, message, load, mutate } = usePortalData('/api/admin/operations');
  const [settingsError, setSettingsError] = useState('');

  async function updateSettings(event) {
    event.preventDefault();
    setSettingsError('');
    const form = new FormData(event.currentTarget);
    const success = await mutate('/api/admin/settings', 'PUT', {
      commission_rate: Number(form.get('commission_rate')),
      refund_policy: 'manual_review',
    }, 'Admin settings saved.');
    if (!success) setSettingsError('Settings could not be saved.');
  }

  return (
    <>
      <SectionCard title="Commission & refund rules" description="Commission is captured on new bookings. Refund decisions require manual review; no payment is automatically refunded by this dashboard.">
        <DashboardStatus error={error} message={message} />
        <Notice error>{settingsError}</Notice>
        {loading && !data && <p className="text-sm text-[#66736d]" role="status">Loading admin operations…</p>}
        {data && <form className="grid gap-4 sm:grid-cols-[12rem_1fr_auto] sm:items-end" onSubmit={updateSettings}>
          <label><span className="field-label">Commission rate (%)</span><input className="field" type="number" name="commission_rate" min="10" max="20" step="0.1" defaultValue={data.settings.commission_rate} required /></label>
          <div className="rounded-xl bg-[#f5f3ed] p-4 text-sm text-[#52615b]">
            <strong className="block text-[#203b35]">Cancellation & refund policy</strong>
            Customer cancellation cutoff: {data.settings.cancellation_window_hours} hours before departure. Paid refunds require manual review and external processing.
          </div>
          <button className="rounded-full bg-[#203b35] px-5 py-3 text-sm font-semibold text-white" type="submit">Save settings</button>
        </form>}
        {!loading && !data && <button className="font-semibold text-[#203b35] underline" type="button" onClick={load}>Retry loading settings</button>}
      </SectionCard>
      {data && <AdminUserManagement customers={data.customers} vendors={data.vendors} onMutation={mutate} />}
      {data && <SectionCard title="Bookings oversight" description={`${data.bookings_truncated ? 'Showing the latest 200 bookings. ' : ''}Review bookings, cancel active reservations, manage refund reviews, and open dispute cases.`}>
        <div className="space-y-4">
          {data.bookings.length === 0 && <p className="rounded-xl bg-[#f5f3ed] p-4 text-sm text-[#66736d]">No bookings have been received.</p>}
          {data.bookings.map((booking) => <AdminBookingCard booking={booking} onMutation={mutate} key={booking.id} />)}
        </div>
      </SectionCard>}
      {data && <AdminDisputes disputes={data.disputes} onMutation={mutate} />}
      {data && <SectionCard title="Booking & revenue analytics" description="Revenue and commission totals include bookings with a successful payment only. Commission uses the rate saved when each booking was created.">
        <div className="grid gap-4 sm:grid-cols-3">
          {[
            ['All bookings', data.analytics.total_bookings],
            ['Paid revenue', `KSh ${formatNumber(data.analytics.paid_revenue)}`],
            ['Commission earned', `KSh ${formatNumber(data.analytics.commission_earned)}`],
          ].map(([label, value]) => <div className="rounded-xl bg-[#f5f3ed] p-4" key={label}><p className="text-sm text-[#66736d]">{label}</p><p className="display-font mt-2 text-2xl text-[#203b35]">{value}</p></div>)}
        </div>
        <div className="mt-5 space-y-3">
          {data.analytics.by_tour.map((tour) => <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#f0ede6] py-3 text-sm" key={tour.tour}>
            <div><p className="font-semibold text-[#203b35]">{tour.tour_name}</p><p className="text-[#66736d]">{tour.bookings} booking{tour.bookings === 1 ? '' : 's'}</p></div>
            <div className="text-right text-[#52615b]"><p>KSh {formatNumber(tour.paid_revenue)} paid</p><p>KSh {formatNumber(tour.commission_earned)} commission</p></div>
          </div>)}
          {data.analytics.by_tour.length === 0 && <p className="text-sm text-[#66736d]">Analytics will appear when bookings are received.</p>}
        </div>
      </SectionCard>}
    </>
  );
}

function ActivityTable({ title, columns, rows, emptyMessage }) {
  return (
    <SectionCard title={title}>
      {rows.length === 0
        ? <p className="rounded-xl bg-[#f5f3ed] p-4 text-sm text-[#66736d]">{emptyMessage}</p>
        : <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-left text-sm">
            <thead><tr className="border-b border-[#e9e5db] text-[#66736d]">{columns.map(([label]) => <th className="px-3 py-3 font-semibold" key={label}>{label}</th>)}</tr></thead>
            <tbody>{rows.map((row) => (
              <tr className="border-b border-[#f0ede6] align-top text-[#52615b]" key={row.id}>
                {columns.map(([label, render]) => <td className="px-3 py-3" key={label}>{render(row)}</td>)}
              </tr>
            ))}</tbody>
          </table>
        </div>}
    </SectionCard>
  );
}

export function AdminActivityDashboardPage() {
  const { data, loading, error, load } = usePortalData('/api/admin/dashboard');
  const [signOutError, setSignOutError] = useState('');
  const signOut = makeSignOut({
    endpoint: '/admin/logout',
    csrfToken: data?.csrf_token,
    redirectTo: '/admin/login',
    onError: setSignOutError,
  });

  if (loading && !data) return <div className="min-h-screen bg-[#f8f7f2]"><PortalHeader role="Admin" actor="Loading your dashboard…" /><main className="mx-auto max-w-7xl px-5 py-10 text-[#66736d]">Loading bookings and messages…</main></div>;
  if (error && !data) return <DashboardLoadError role="Admin" error={error} onRetry={load} />;

  return (
    <DashboardLayout role="Admin" actor="Bookings and messages" signOut={signOut}>
      <DashboardStatus error={error || signOutError} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-[#66736d]">A clear view of the latest guest enquiries and tour booking activity across Lamu.</p>
        <a className="font-semibold text-[#9a5534] hover:underline" href="/admin">Catalog and accounts →</a>
      </div>
      {data && <div className="grid gap-4 sm:grid-cols-2">
        {[
          ['Total contact messages', data.total_submissions],
          ['Total booking requests', data.total_bookings],
          ['Recent messages shown', data.recent_submissions.length],
          ['Recent bookings shown', data.recent_bookings.length],
        ].map(([label, count]) => <div className="rounded-2xl border border-[#e9e5db] bg-white p-5" key={label}><p className="text-sm text-[#66736d]">{label}</p><p className="display-font mt-2 text-3xl text-[#203b35]">{count}</p></div>)}
      </div>}
      {data && <ActivityTable
        title="Latest contact submissions"
        rows={data.recent_submissions}
        emptyMessage="No submissions have been received yet."
        columns={[
          ['#', (item) => item.id],
          ['Name', (item) => item.name],
          ['Email', (item) => item.email],
          ['Subject', (item) => item.subject],
          ['Received', (item) => displayTimestamp(item.timestamp)],
          ['Email sent', (item) => item.email_sent ? 'Yes' : 'No'],
        ]}
      />}
      {data && <ActivityTable
        title="Latest booking requests"
        rows={data.recent_bookings}
        emptyMessage="No booking requests have been received yet."
        columns={[
          ['#', (item) => item.id],
          ['Name', (item) => item.name],
          ['Email', (item) => item.email],
          ['Phone', (item) => item.phone],
          ['Tour', (item) => item.tour],
          ['Date', (item) => item.date],
          ['Time', (item) => item.time],
          ['Guests', (item) => item.guests],
        ]}
      />}
    </DashboardLayout>
  );
}

export function AdminDashboardPage() {
  const { data, loading, error, message, load, mutate } = usePortalData('/api/admin/catalogue');
  const [signOutError, setSignOutError] = useState('');
  const signOut = makeSignOut({
    endpoint: '/admin/logout',
    csrfToken: data?.csrf_token,
    redirectTo: '/admin/login',
    onError: setSignOutError,
  });

  if (loading && !data) return <div className="min-h-screen bg-[#f8f7f2]"><PortalHeader role="Admin" actor="Loading your dashboard…" /><main className="mx-auto max-w-7xl px-5 py-10 text-[#66736d]">Loading catalogue…</main></div>;
  if (error && !data) return <DashboardLoadError role="Admin" error={error} onRetry={load} />;

  const vendorOwner = (item) => item.vendor_id
    ? `Vendor listing · ${data.vendors.find((vendor) => vendor.id === item.vendor_id)?.name || 'Vendor'}`
    : 'Managed by Lamu Tours';

  return (
    <DashboardLayout role="Admin" actor="Catalog management" signOut={signOut}>
      <DashboardStatus error={error || signOutError} message={message} />
      <p className="text-sm text-[#66736d]">Shape the experiences guests discover, support local operators, and keep an eye on how the marketplace is growing.</p>
      <AdminOperationsSection />
      {data && <div className="grid gap-4 sm:grid-cols-3">
        {[
          ['Tours', data.tours.length],
          ['Properties', data.properties.length],
          ['Vendors', data.vendors.length],
        ].map(([label, count]) => <div className="rounded-2xl border border-[#e9e5db] bg-white p-5" key={label}><p className="text-sm text-[#66736d]">{label}</p><p className="display-font mt-2 text-3xl text-[#203b35]">{count}</p></div>)}
      </div>}
      {data && <CatalogSection title="Tours" items={data.tours} fields={tourFields} basePath="/api/admin/tours" onMutation={mutate} ownerLabel={vendorOwner} csrfToken={data.csrf_token} />}
      {data && <AvailabilitySection tours={data.tours} endpoint="/api/admin/availability" csrfToken={data.csrf_token} />}
      {data && <CatalogSection title="Properties" items={data.properties} fields={propertyFields} basePath="/api/admin/properties" onMutation={mutate} ownerLabel={vendorOwner} csrfToken={data.csrf_token} />}
      {data && <CatalogSection title="Trending destinations" items={data.destinations} fields={destinationFields} basePath="/api/admin/destinations" onMutation={mutate} csrfToken={data.csrf_token} />}
      {data && <AdminAccounts admins={data.admins} vendors={data.vendors} onMutation={mutate} />}
      <a className="inline-flex font-semibold text-[#9a5534] hover:underline" href="/dashboard">Open bookings and messages →</a>
    </DashboardLayout>
  );
}

export function VendorDashboardPage() {
  const { data, loading, error, message, load, mutate } = usePortalData('/api/vendor/catalogue');
  const [signOutError, setSignOutError] = useState('');
  const signOut = makeSignOut({
    endpoint: '/vendor/logout',
    csrfToken: data?.csrf_token,
    redirectTo: '/vendor/login',
    onError: setSignOutError,
  });

  if (loading && !data) return <div className="min-h-screen bg-[#f8f7f2]"><PortalHeader role="Vendor" actor="Loading your dashboard…" /><main className="mx-auto max-w-7xl px-5 py-10 text-[#66736d]">Loading your listings…</main></div>;
  if (error && !data) return <DashboardLoadError role="Vendor" error={error} onRetry={load} />;

  return (
    <DashboardLayout role="Vendor" actor={data?.vendor.name || 'Your listings'} signOut={signOut}>
      <DashboardStatus error={error || signOutError} message={message} />
      {data && <p className="text-sm text-[#66736d]">Welcome, {data.vendor.name}. Your tours, stays, departures, and guest bookings are gathered here. Signed in as {data.vendor.email}.</p>}
      {data && <div className="grid gap-4 sm:grid-cols-2">
        {[
          ['Your tours', data.tours.length],
          ['Your properties', data.properties.length],
        ].map(([label, count]) => <div className="rounded-2xl border border-[#e9e5db] bg-white p-5" key={label}><p className="text-sm text-[#66736d]">{label}</p><p className="display-font mt-2 text-3xl text-[#203b35]">{count}</p></div>)}
      </div>}
      {data && <CatalogSection title="Tours" items={data.tours} fields={tourFields} basePath="/api/vendor/tours" onMutation={mutate} csrfToken={data.csrf_token} />}
      {data && <AvailabilitySection tours={data.tours} endpoint="/api/vendor/availability" csrfToken={data.csrf_token} />}
      {data && <CatalogSection title="Properties" items={data.properties} fields={propertyFields} basePath="/api/vendor/properties" onMutation={mutate} csrfToken={data.csrf_token} />}
      {data && <VendorBookingsSection csrfToken={data.csrf_token} />}
    </DashboardLayout>
  );
}
