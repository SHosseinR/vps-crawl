import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Link, NavLink, Route, BrowserRouter as Router, Routes, useSearchParams } from "react-router-dom";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Cpu,
  Database,
  ExternalLink,
  Filter,
  Gauge,
  HardDrive,
  MemoryStick,
  MonitorUp,
  Search,
  Server,
  Zap,
} from "lucide-react";
import "./styles.css";

const PAGE_SIZE = 50;

const SORT_FIELDS = [
  ["equivalent_hourly_price_toman", "قیمت معادل ساعتی"],
  ["cpu_cores", "CPU"],
  ["ram_mb", "RAM"],
  ["disk_gb", "دیسک"],
  ["gpu_memory_mb", "حافظه GPU"],
];

const SORT_DIRECTIONS = [
  ["asc", "صعودی"],
  ["desc", "نزولی"],
];

const EMPTY_FILTERS = {
  search: "",
  provider: "",
  region: "",
  billing_period: "",
  price_min: "",
  price_max: "",
  min_cpu_cores: "",
  max_cpu_cores: "",
  min_ram_mb: "",
  max_ram_mb: "",
  min_disk_gb: "",
  max_disk_gb: "",
  gpu_model: "",
  min_gpu_memory_mb: "",
  max_gpu_memory_mb: "",
  sort_by: "equivalent_hourly_price_toman",
  sort_dir: "asc",
};

const PERIOD_LABELS = {
  hourly: "ساعتی",
  hour: "ساعتی",
  daily: "روزانه",
  day: "روزانه",
  weekly: "هفتگی",
  week: "هفتگی",
  monthly: "ماهیانه",
  month: "ماهیانه",
  yearly: "سالانه",
  year: "سالانه",
};

const REGION_LABELS = {
  iran: "ایران",
  europe: "اروپا",
  germany: "آلمان",
  france: "فرانسه",
  finland: "فنلاند",
  usa: "آمریکا",
  unknown: "نامشخص",
};

function App() {
  return (
    <Router>
      <div className="app-shell" dir="rtl">
        <header className="topbar">
          <Link to="/" className="brand">
            <Server size={22} />
            <span>بازار VPS</span>
          </Link>
          <nav className="nav">
            <NavLink to="/" end>
              همه سرورها
            </NavLink>
            <NavLink to="/gpu">
              <Zap size={16} />
              GPU
            </NavLink>
          </nav>
        </header>
        <Routes>
          <Route path="/" element={<OffersPage mode="all" />} />
          <Route path="/gpu" element={<OffersPage mode="gpu" />} />
        </Routes>
      </div>
    </Router>
  );
}

function OffersPage({ mode }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [options, setOptions] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState({});

  const filters = useMemo(() => filtersFromParams(searchParams, mode), [searchParams, mode]);
  const page = Number(searchParams.get("page") || "1");

  useEffect(() => {
    fetch("/api/filter-options/")
      .then((response) => response.json())
      .then(setOptions)
      .catch(() => setOptions({ providers: [], regions: [], disk_types: [], gpu_specs: [] }));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");

    fetch(`/api/offers/?${buildOfferQuery(filters, page, mode)}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then(setData)
      .catch((err) => {
        if (err.name !== "AbortError") setError("امکان دریافت پیشنهادها وجود ندارد.");
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [filters, page, mode]);

  const updateFilter = (name, value) => {
    const next = new URLSearchParams(searchParams);
    const updates = typeof name === "object" ? name : { [name]: value };
    for (const [key, nextValue] of Object.entries(updates)) {
      if (nextValue) next.set(key, nextValue);
      else next.delete(key);
    }
    if (Object.hasOwn(updates, "billing_period")) {
      next.delete("price_min");
      next.delete("price_max");
      next.delete("min_price_toman");
      next.delete("max_price_toman");
      next.delete("min_equivalent_hourly_price_toman");
      next.delete("max_equivalent_hourly_price_toman");
    }
    next.delete("region_detail");
    next.delete("page");
    setSearchParams(next);
  };

  const clearFilters = () => {
    const next = new URLSearchParams({ sort_by: "equivalent_hourly_price_toman", sort_dir: "asc" });
    setSearchParams(next);
  };

  const totalPages = Math.max(1, Math.ceil((data?.count || 0) / PAGE_SIZE));
  const title = mode === "gpu" ? "سرورهای GPU" : "همه سرورها";
  const subtitle =
    mode === "gpu"
      ? "اول GPU و حافظه گرافیکی را ببین، بعد مشخصات VM را مقایسه کن."
      : "پیشنهادها بر اساس قیمت معادل ساعتی از ارزان ترین مرتب شده اند.";

  return (
    <main className="workspace">
      <section className="summary-band">
        <div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        <ModeSwitch activeMode={mode} />
      </section>

      <section className="content-grid">
        <aside className="filters-panel">
          <div className="panel-title">
            <Filter size={18} />
            <span>فیلترها</span>
          </div>
          <FilterControls filters={filters} options={options} mode={mode} onChange={updateFilter} onClear={clearFilters} />
        </aside>

        <section className="offers-panel">
          <div className="list-toolbar">
            <div className="count">
              <strong>{formatNumber(data?.count ?? 0)}</strong>
              <span>نتیجه</span>
            </div>
            <div className="sort-controls">
              <label className="select-wrap">
                <span>مرتب سازی</span>
                <select value={filters.sort_by} onChange={(event) => updateFilter("sort_by", event.target.value)}>
                  {SORT_FIELDS.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="select-wrap compact">
                <span>جهت</span>
                <select value={filters.sort_dir} onChange={(event) => updateFilter("sort_dir", event.target.value)}>
                  {SORT_DIRECTIONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
                </select>
              </label>
            </div>
          </div>

          {error && <div className="state-box error">{error}</div>}
          {loading && <div className="state-box">در حال دریافت پیشنهادها...</div>}
          {!loading && !error && data?.results?.length === 0 && <div className="state-box">پیشنهادی پیدا نشد.</div>}

          <div className="offer-list">
            {data?.results?.map((offer) => (
              <OfferRow
                key={offer.id}
                offer={offer}
                gpuFirst={mode === "gpu"}
                expanded={!!expanded[offer.id]}
                onToggle={() => setExpanded((current) => ({ ...current, [offer.id]: !current[offer.id] }))}
              />
            ))}
          </div>

          <Pagination page={page} totalPages={totalPages} setPage={(nextPage) => {
            const next = new URLSearchParams(searchParams);
            if (nextPage <= 1) next.delete("page");
            else next.set("page", String(nextPage));
            setSearchParams(next);
          }} />
        </section>
      </section>
    </main>
  );
}

function ModeSwitch({ activeMode }) {
  return (
    <div className="mode-switch" aria-label="نوع پیشنهادها">
      <Link to="/" className={activeMode === "all" ? "active" : ""}>
        <Server size={19} />
        همه سرورها
      </Link>
      <Link to="/gpu" className={activeMode === "gpu" ? "active gpu" : "gpu"}>
        <Zap size={21} />
        فقط GPU
      </Link>
    </div>
  );
}

function FilterControls({ filters, options, mode, onChange, onClear }) {
  const gpuSpecs = options?.gpu_specs || [];
  const bounds = options?.bounds || {};
  const priceConfig = priceFilterConfig(filters.billing_period);

  const onRangeChange = (minKey, maxKey, range, nextMin, nextMax) => {
    onChange({
      [minKey]: nextMin <= range.min ? "" : String(nextMin),
      [maxKey]: nextMax >= range.max ? "" : String(nextMax),
    });
  };

  return (
    <div className="filters">
      <Select label="دوره پرداخت" value={filters.billing_period} onChange={(value) => onChange("billing_period", value)}>
        <option value="">همه</option>
        {(options?.billing_periods || []).map((period) => (
          <option key={period} value={period}>
            {periodLabel(period)}
          </option>
        ))}
      </Select>

      <RangeFilter
        label={priceConfig.label}
        unit="تومان"
        hint={priceConfig.hint}
        bounds={{ min: priceConfig.min, max: priceConfig.max }}
        minValue={filters.price_min}
        maxValue={filters.price_max}
        step={priceConfig.step}
        format={formatPrice}
        onChange={(min, max, range) => onRangeChange("price_min", "price_max", range, min, max)}
      />

      {mode === "gpu" && (
        <Select label="مدل GPU" value={filters.gpu_model} onChange={(value) => onChange("gpu_model", value)}>
          <option value="">همه</option>
          {gpuSpecs.map((gpu) => (
            <option key={gpu.id} value={gpu.model}>
              {gpu.model}{gpu.memory_mb ? ` ${formatMemory(gpu.memory_mb)}` : ""}
            </option>
          ))}
        </Select>
      )}

      {mode === "gpu" && (
        <RangeFilter
          label="حافظه GPU"
          unit="VRAM"
          bounds={rangeBounds(bounds.gpu_memory_mb, 0, 81920)}
          minValue={filters.min_gpu_memory_mb}
          maxValue={filters.max_gpu_memory_mb}
          step={1024}
          format={formatMemory}
          onChange={(min, max, range) => onRangeChange("min_gpu_memory_mb", "max_gpu_memory_mb", range, min, max)}
        />
      )}

      <RangeFilter
        label="CPU"
        unit="هسته"
        bounds={rangeBounds(bounds.cpu_cores, 0, 128)}
        minValue={filters.min_cpu_cores}
        maxValue={filters.max_cpu_cores}
        step={1}
        format={(value) => `${formatNumber(value)} هسته`}
        onChange={(min, max, range) => onRangeChange("min_cpu_cores", "max_cpu_cores", range, min, max)}
      />

      <RangeFilter
        label="RAM"
        unit="حافظه"
        bounds={rangeBounds(bounds.ram_mb, 0, 524288)}
        minValue={filters.min_ram_mb}
        maxValue={filters.max_ram_mb}
        step={1024}
        format={formatMemory}
        onChange={(min, max, range) => onRangeChange("min_ram_mb", "max_ram_mb", range, min, max)}
      />

      <RangeFilter
        label="دیسک"
        unit="GB"
        bounds={{ min: 10, max: 2048 }}
        minValue={filters.min_disk_gb}
        maxValue={filters.max_disk_gb}
        step={10}
        format={formatDisk}
        onChange={(min, max, range) => onRangeChange("min_disk_gb", "max_disk_gb", range, min, max)}
      />

      <Select label="ارائه دهنده" value={filters.provider} onChange={(value) => onChange("provider", value)}>
        <option value="">همه</option>
        {(options?.providers || []).map((provider) => (
          <option key={provider.slug} value={provider.slug}>
            {provider.name}
          </option>
        ))}
      </Select>

      <Select label="منطقه" value={filters.region} onChange={(value) => onChange("region", value)}>
        <option value="">همه</option>
        {(options?.regions || []).map((region) => (
          <option key={region} value={region}>
            {regionLabel(region)}
          </option>
        ))}
      </Select>

      {mode !== "gpu" && (
        <Select label="مدل GPU" value={filters.gpu_model} onChange={(value) => onChange("gpu_model", value)}>
          <option value="">همه</option>
          {gpuSpecs.map((gpu) => (
            <option key={gpu.id} value={gpu.model}>
              {gpu.model}{gpu.memory_mb ? ` ${formatMemory(gpu.memory_mb)}` : ""}
            </option>
          ))}
        </Select>
      )}

      <label className="input-wrap wide">
        <span>جستجو</span>
        <div className="search-input">
          <Search size={16} />
          <input value={filters.search} onChange={(event) => onChange("search", event.target.value)} placeholder="RTX، تهران، CX..." />
        </div>
      </label>

      <button className="clear-btn" type="button" onClick={onClear}>
        پاک کردن فیلترها
      </button>
    </div>
  );
}

function Select({ label, value, onChange, children }) {
  return (
    <label className="input-wrap">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {children}
      </select>
    </label>
  );
}

function RangeFilter({ label, unit, hint, bounds, minValue, maxValue, step, format, onChange }) {
  const range = bounds || { min: 0, max: 0 };
  const disabled = range.max <= range.min;
  const selectedMin = snapToStep(clampNumber(minValue, range.min, range.max, range.min), range.min, range.max, step);
  const selectedMax = snapToStep(clampNumber(maxValue, range.min, range.max, range.max), range.min, range.max, step);
  const min = Math.min(selectedMin, selectedMax);
  const max = Math.max(selectedMin, selectedMax);
  const minPosition = disabled ? 0 : valueToLogPosition(min, range, step);
  const maxPosition = disabled ? 1000 : valueToLogPosition(max, range, step);
  const minPercent = minPosition / 10;
  const maxPercent = maxPosition / 10;
  const left = disabled ? 0 : 100 - maxPercent;
  const right = disabled ? 0 : minPercent;
  const positionToValue = (position) => snapToStep(logPositionToValue(Number(position), range, step), range.min, range.max, step);

  return (
    <div className={`range-filter ${disabled ? "disabled" : ""}`}>
      <div className="range-head">
        <span>{label}</span>
        <small>{unit}</small>
      </div>
      {hint && <p className="range-hint">{hint}</p>}
      <div className="range-values">
        <strong>{format(min)}</strong>
        <strong>{format(max)}</strong>
      </div>
      <div className="range-slider" style={{ "--range-left": `${left}%`, "--range-right": `${right}%` }}>
        <input
          type="range"
          min="0"
          max="1000"
          step="1"
          value={minPosition}
          disabled={disabled}
          onChange={(event) => onChange(Math.min(positionToValue(event.target.value), max), max, range)}
          aria-label={`${label} حداقل`}
        />
        <input
          type="range"
          min="0"
          max="1000"
          step="1"
          value={maxPosition}
          disabled={disabled}
          onChange={(event) => onChange(min, Math.max(positionToValue(event.target.value), min), range)}
          aria-label={`${label} حداکثر`}
        />
      </div>
    </div>
  );
}

function OfferRow({ offer, expanded, onToggle, gpuFirst }) {
  const providerUrl = offer.provider?.base_url || offer.source_url;
  const primarySpecs = gpuFirst ? gpuSpecs(offer).concat(vmSpecs(offer).slice(0, 3)) : vmSpecs(offer).concat(gpuSpecs(offer));

  return (
    <article className={`offer-row ${offer.has_gpu ? "gpu-offer" : ""}`}>
      <div className="offer-main">
        <button className="expand-btn" onClick={onToggle} aria-label={expanded ? "بستن جزئیات" : "نمایش جزئیات"}>
          {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
        <div className="offer-heading">
          <div className="title-line">
            <h2>{offer.name}</h2>
            {offer.has_gpu && <span className="gpu-pill"><Zap size={14} /> GPU</span>}
          </div>
          <div className="meta-line">
            {providerUrl ? (
              <a href={providerUrl} target="_blank" rel="noreferrer" className="provider-link">
                {offer.provider?.name || "ارائه دهنده"}
                <ExternalLink size={13} />
              </a>
            ) : (
              <span>{offer.provider?.name}</span>
            )}
            <span>{regionLabel(offer.region)}</span>
            {offer.region_detail && <span>{offer.region_detail}</span>}
          </div>
        </div>
        <div className="price-box">
          <div className="price-card">
            <div className="price-line">
              <strong>{formatPrice(offer.price_amount_toman)}</strong>
              <span>تومان</span>
              <b className={`period-badge ${periodTone(offer.billing_period)}`}>{periodLabel(offer.billing_period)}</b>
            </div>
          </div>
          <div className="period-card">
            {offer.equivalent_hourly_price_toman && (
              <small>معادل ساعتی {formatPrice(offer.equivalent_hourly_price_toman)} تومان</small>
            )}
          </div>
        </div>
        <a className="buy-btn" href={offer.buy_url || offer.source_url || providerUrl || "#"} target="_blank" rel="noreferrer">
          خرید
          <ExternalLink size={16} />
        </a>
      </div>

      <div className={`spec-strip ${gpuFirst ? "gpu-first" : ""}`}>
        {primarySpecs.map((spec) => (
          <Spec key={spec.label} {...spec} />
        ))}
      </div>

      {expanded && (
        <div className="details">
          {offer.gpu && <DetailBlock title="مشخصات GPU" items={gpuSpecs(offer)} />}
          <DetailBlock title="مشخصات VM" items={vmSpecs(offer)} />
          <DetailBlock
            title="بازار"
            items={[
              { label: "کشور", value: offer.country || "-" },
              { label: "شهر", value: offer.city || "-" },
              { label: "منطقه دقیق", value: offer.region_detail || "-" },
              { label: "دسته بندی", value: offer.category || "-" },
              { label: "وضعیت", value: offer.available ? "موجود" : "ناموجود" },
              { label: "شناسه منبع", value: offer.source_offer_id },
            ]}
          />
        </div>
      )}
    </article>
  );
}

function Spec({ icon: Icon, label, value, important }) {
  return (
    <div className={`spec ${important ? "important" : ""}`}>
      <Icon size={17} />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DetailBlock({ title, items }) {
  return (
    <section className="detail-block">
      <h3>{title}</h3>
      <dl>
        {items.map((item) => (
          <React.Fragment key={item.label}>
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </React.Fragment>
        ))}
      </dl>
    </section>
  );
}

function Pagination({ page, totalPages, setPage }) {
  return (
    <div className="pagination">
      <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1} aria-label="صفحه قبل">
        <ChevronRight size={17} />
      </button>
      <span>
        {formatNumber(page)} / {formatNumber(totalPages)}
      </span>
      <button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page >= totalPages} aria-label="صفحه بعد">
        <ChevronLeft size={17} />
      </button>
    </div>
  );
}

function vmSpecs(offer) {
  return [
    { icon: Cpu, label: "CPU", value: offer.cpu_cores ? `${formatNumber(offer.cpu_cores)} هسته` : "-" },
    { icon: MemoryStick, label: "RAM", value: formatMemory(offer.ram_mb) },
    { icon: HardDrive, label: "دیسک", value: `${formatNumber(offer.disk_gb)} GB${offer.disk_type ? ` ${offer.disk_type}` : ""}` },
    { icon: Gauge, label: "ترافیک", value: offer.traffic_gb ? `${formatNumber(offer.traffic_gb)} GB` : "-" },
    { icon: MonitorUp, label: "پهنای باند", value: offer.bandwidth_mbps ? `${formatNumber(offer.bandwidth_mbps)} Mbps` : "-" },
  ];
}

function gpuSpecs(offer) {
  if (!offer.gpu) return [];
  return [
    { icon: Zap, label: "GPU", value: offer.gpu.model, important: true },
    { icon: Database, label: "VRAM", value: formatMemory(offer.gpu.memory_mb), important: true },
  ];
}

function filtersFromParams(params, mode) {
  const filters = { ...EMPTY_FILTERS };
  for (const key of Object.keys(filters)) {
    filters[key] = params.get(key) || filters[key];
  }
  filters.price_min =
    params.get("price_min") ||
    params.get("min_price_toman") ||
    params.get("min_equivalent_hourly_price_toman") ||
    filters.price_min;
  filters.price_max =
    params.get("price_max") ||
    params.get("max_price_toman") ||
    params.get("max_equivalent_hourly_price_toman") ||
    filters.price_max;
  const legacyOrdering = params.get("ordering");
  if (legacyOrdering) {
    filters.sort_by = legacyOrdering.replace("-", "");
    filters.sort_dir = legacyOrdering.startsWith("-") ? "desc" : "asc";
  }
  return filters;
}

function buildOfferQuery(filters, page, mode) {
  const params = new URLSearchParams();
  const priceConfig = priceFilterConfig(filters.billing_period);
  const skipKeys = new Set(["price_min", "price_max"]);
  for (const [key, value] of Object.entries(filters)) {
    if (value && !skipKeys.has(key)) params.set(key, value);
  }
  const minPrice = clampNumber(filters.price_min, priceConfig.min, priceConfig.max, priceConfig.min);
  const maxPrice = clampNumber(filters.price_max, priceConfig.min, priceConfig.max, priceConfig.max);
  if (filters.price_min && minPrice > priceConfig.min) params.set(priceConfig.minParam, String(minPrice));
  if (filters.price_max && maxPrice < priceConfig.max) params.set(priceConfig.maxParam, String(maxPrice));
  if (mode === "gpu") params.set("has_gpu", "true");
  params.set("page", String(page));
  return params.toString();
}

function formatPrice(value) {
  if (value === null || value === undefined || value === "") return "تماس بگیرید";
  return Math.round(Number(value)).toLocaleString("fa-IR", { maximumFractionDigits: 0 });
}

function formatMemory(value) {
  if (!value) return "-";
  if (value >= 1024) return `${formatNumber(value / 1024)} GB`;
  return `${formatNumber(value)} MB`;
}

function formatDisk(value) {
  if (!value) return "-";
  if (value >= 1024) return `${formatNumber(value / 1024)} TB`;
  return `${formatNumber(value)} GB`;
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  return Number.isInteger(number) ? number.toLocaleString("fa-IR") : number.toLocaleString("fa-IR", { maximumFractionDigits: 1 });
}

function periodLabel(value) {
  return PERIOD_LABELS[String(value || "").toLowerCase()] || value || "-";
}

function periodTone(value) {
  const period = String(value || "").toLowerCase();
  if (period === "monthly" || period === "month") return "monthly";
  if (period === "hourly" || period === "hour") return "hourly";
  return "neutral";
}

function regionLabel(value) {
  return REGION_LABELS[String(value || "").toLowerCase()] || value || "-";
}

function priceFilterConfig(billingPeriod) {
  const period = String(billingPeriod || "").toLowerCase();
  if (!period) {
    return {
      label: "قیمت معادل ساعتی",
      hint: "تا وقتی دوره پرداخت انتخاب نشده، فیلتر قیمت بر اساس معادل ساعتی محاسبه می شود.",
      min: 10000,
      max: 2000000,
      step: 10000,
      minParam: "min_equivalent_hourly_price_toman",
      maxParam: "max_equivalent_hourly_price_toman",
    };
  }
  if (period === "hourly" || period === "hour") {
    return {
      label: "قیمت ساعتی",
      hint: "با انتخاب دوره پرداخت، فیلتر قیمت روی قیمت همان دوره اعمال می شود.",
      min: 10000,
      max: 2000000,
      step: 10000,
      minParam: "min_price_toman",
      maxParam: "max_price_toman",
    };
  }
  if (period === "monthly" || period === "month") {
    return {
      label: "قیمت ماهانه",
      hint: "با انتخاب دوره پرداخت، فیلتر قیمت روی قیمت همان دوره اعمال می شود.",
      min: 1000000,
      max: 500000000,
      step: 1000000,
      minParam: "min_price_toman",
      maxParam: "max_price_toman",
    };
  }
  return {
    label: `قیمت ${periodLabel(period)}`,
    hint: "با انتخاب دوره پرداخت، فیلتر قیمت روی قیمت همان دوره اعمال می شود.",
    min: 10000,
    max: 500000000,
    step: 100000,
    minParam: "min_price_toman",
    maxParam: "max_price_toman",
  };
}

function rangeBounds(value, fallbackMin, fallbackMax) {
  const min = Number(value?.min ?? fallbackMin);
  const max = Number(value?.max ?? fallbackMax);
  if (!Number.isFinite(min) || !Number.isFinite(max) || max <= min) {
    return { min: fallbackMin, max: fallbackMax };
  }
  return { min: Math.floor(min), max: Math.ceil(max) };
}

function clampNumber(value, min, max, fallback) {
  if (value === "" || value === null || value === undefined) return fallback;
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

function valueToLogPosition(value, range, step) {
  const span = range.max - range.min;
  if (span <= 0) return 0;
  const scale = Math.max(Number(step) || 1, 1);
  const normalized = Math.max(0, value - range.min);
  return Math.round((Math.log1p(normalized / scale) / Math.log1p(span / scale)) * 1000);
}

function logPositionToValue(position, range, step) {
  const span = range.max - range.min;
  if (span <= 0) return range.min;
  const scale = Math.max(Number(step) || 1, 1);
  const ratio = Math.min(1000, Math.max(0, position)) / 1000;
  return range.min + scale * (Math.expm1(ratio * Math.log1p(span / scale)));
}

function snapToStep(value, min, max, step) {
  const stepSize = Math.max(Number(step) || 1, 1);
  const snapped = min + Math.round((value - min) / stepSize) * stepSize;
  return Math.min(max, Math.max(min, snapped));
}

createRoot(document.getElementById("root")).render(<App />);
