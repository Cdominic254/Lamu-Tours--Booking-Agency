(() => {
    const dataKey = 'lamu-tours-currency-data';
    const dataMaxAge = 12 * 60 * 60 * 1000;
    let rates = { KES: 1 };
    let currentCurrency = 'KES';

    function readStorage(key) {
        try {
            return window.localStorage.getItem(key);
        } catch (error) {
            console.warn(`Could not read ${key} from browser storage.`, error);
            return null;
        }
    }

    function writeStorage(key, value) {
        try {
            window.localStorage.setItem(key, value);
        } catch (error) {
            console.warn(`Could not save ${key} in browser storage.`, error);
        }
    }

    function format(amount) {
        const code = Object.hasOwn(rates, currentCurrency) ? currentCurrency : 'KES';
        const converted = amount * rates[code];
        const locale = document.documentElement.lang === 'sw' ? 'sw-KE' : 'en-KE';
        return new Intl.NumberFormat(locale, {
            style: 'currency',
            currency: code,
            maximumFractionDigits: code === 'KES' ? 0 : 2,
        }).format(converted);
    }

    function renderPrices() {
        document.querySelectorAll('[data-price-kes]').forEach((element) => {
            const amount = Number(element.dataset.priceKes);
            if (!Number.isFinite(amount) || amount < 0) {
                console.error('Invalid KES amount for displayed price.', element);
                return;
            }

            const label = document.documentElement.lang === 'sw'
                ? element.dataset.priceLabelSw
                : element.dataset.priceLabelEn;
            const unit = document.documentElement.lang === 'sw'
                ? element.dataset.priceUnitSw
                : element.dataset.priceUnitEn;
            const text = `${label || ''}${format(amount)}${unit ? ` ${unit}` : ''}`;
            if (element.textContent !== text) element.textContent = text;
        });

        document.querySelectorAll('option[data-price-kes]').forEach((option) => {
            const label = document.documentElement.lang === 'sw'
                ? option.dataset.labelSw
                : option.dataset.labelEn;
            const unit = document.documentElement.lang === 'sw'
                ? option.dataset.unitSw
                : option.dataset.unitEn;
            const text = `${label} — ${format(Number(option.dataset.priceKes))}${unit ? ` ${unit}` : ''}`;
            if (option.textContent !== text) option.textContent = text;
        });

        document.querySelectorAll('[data-language-toggle]').forEach((button) => {
            button.setAttribute('aria-pressed', String(document.documentElement.lang === 'sw'));
        });
    }

    function applyDetectedCurrency(currency) {
        currentCurrency = Object.hasOwn(rates, currency) ? currency : 'KES';
        renderPrices();
        document.dispatchEvent(new CustomEvent('lamu-currency-changed', {
            detail: { currency: currentCurrency, rates },
        }));
    }

    function validCurrencyData(data) {
        return data &&
            typeof data === 'object' &&
            data.base === 'KES' &&
            typeof data.currency === 'string' &&
            /^[A-Z]{3}$/.test(data.currency) &&
            typeof data.detected === 'boolean' &&
            typeof data.rates === 'object' &&
            data.rates !== null &&
            data.rates.KES === 1 &&
            Object.entries(data.rates).every(([code, rate]) =>
                /^[A-Z]{3}$/.test(code) && Number.isFinite(rate) && rate > 0);
    }

    async function loadCurrencyData() {
        const cached = readStorage(dataKey);
        if (cached) {
            try {
                const parsed = JSON.parse(cached);
                const age = Date.now() - parsed.savedAt;
                if (Number.isFinite(parsed.savedAt) && age >= 0 && age < dataMaxAge && validCurrencyData(parsed.data)) {
                    return parsed.data;
                }
            } catch (error) {
                console.warn('Saved currency data could not be read; requesting fresh rates.', error);
            }
        }

        const response = await fetch('/api/currency', { headers: { Accept: 'application/json' } });
        if (!response.ok) throw new Error(`Currency service returned HTTP ${response.status}.`);
        const data = await response.json();
        if (!validCurrencyData(data)) throw new Error('Currency service returned invalid data.');
        writeStorage(dataKey, JSON.stringify({ savedAt: Date.now(), data }));
        return data;
    }

    document.addEventListener('lamu-language-changed', renderPrices);

    const priceObserver = new MutationObserver((mutations) => {
        if (mutations.some((mutation) => mutation.type === 'childList' || mutation.attributeName === 'data-price-kes')) {
            renderPrices();
        }
    });
    priceObserver.observe(document.documentElement, {
        subtree: true,
        childList: true,
        attributes: true,
        attributeFilter: ['data-price-kes'],
    });

    (async () => {
        try {
            const data = await loadCurrencyData();
            rates = data.rates;
            if (!data.detected) {
                console.warn('Could not detect a visitor currency; displaying KSh by default.');
            }
            applyDetectedCurrency(data.currency);
        } catch (error) {
            console.error('Could not load currency data; keeping prices in KSh.', error);
            rates = { KES: 1 };
            applyDetectedCurrency('KES');
        }
    })();
})();
