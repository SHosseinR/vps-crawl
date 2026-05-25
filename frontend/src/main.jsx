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
  Sparkles,
  Zap,
} from "lucide-react";
import "./styles.css";

const PAGE_SIZE = 50;

const SORT_OPTIONS = [
  ["price_amount_irr", "Lowest price"],
  ["-price_amount_irr", "Highest price"],
  ["-cpu_cores", "Most CPU"],
  ["-ram_mb", "Most RAM"],
  ["-disk_gb", "Most disk"],
  ["-traffic_gb", "Most traffic"],
  ["-gpu_memory_mb", "Most GPU VRAM"],
  ["provider", "Provider"],
];

const EMPTY_FILTERS = {
  search: "",
  provider: "",
  region: "",
  region_detail: "",
  billing_period: "",
  disk_type: "",
  min_price_irr: "",
  max_price_irr: "",
  min_cpu_cores: "",
  min_ram_mb: "",
  min_disk_gb: "",
  gpu_model: "",
  min_gpu_memory_mb: "",
  ordering: "price_amount_irr",
};

function App() {
  return (
    <Router>
      <div className="app-shell">
        <header className="topbar">
          <Link to="/" className="brand">
            <Server size={22} />
            <span>VPS Market</span>
          </Link>
          <nav className="nav">
            <NavLink to="/" end>
              Offers
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
      .catch(() => setOptions({ providers: [], regions: [], region_details: [], disk_types: [], gpu_specs: [] }));
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
        if (err.name !== "AbortError") setError("Could not load offers.");
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [filters, page, mode]);

  const updateFilter = (name, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(name, value);
    else next.delete(name);
    next.delete("page");
    setSearchParams(next);
  };

  const clearFilters = () => setSearchParams(mode === "gpu" ? new URLSearchParams({ ordering: "price_amount_irr" }) : new URLSearchParams());

  const totalPages = Math.max(1, Math.ceil((data?.count || 0) / PAGE_SIZE));
  const title = mode === "gpu" ? "GPU Offers" : "Offers";
  const subtitle = mode === "gpu" ? "Accelerated plans sorted by price" : "Every VM sorted by price";

  return (
    <main className="workspace">
      <section className="summary-band">
        <div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        <GpuAction active={mode === "gpu"} />
      </section>

      <section className="content-grid">
        <aside className="filters-panel">
          <div className="panel-title">
            <Filter size={18} />
            <span>Filters</span>
          </div>
          <FilterControls filters={filters} options={options} mode={mode} onChange={updateFilter} onClear={clearFilters} />
        </aside>

        <section className="offers-panel">
          <div className="list-toolbar">
            <div className="count">
              <strong>{data?.count ?? 0}</strong>
              <span>matches</span>
            </div>
            <label className="select-wrap">
              <span>Sort</span>
              <select value={filters.ordering} onChange={(event) => updateFilter("ordering", event.target.value)}>
                {SORT_OPTIONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {error && <div className="state-box error">{error}</div>}
          {loading && <div className="state-box">Loading offers...</div>}
          {!loading && !error && data?.results?.length === 0 && <div className="state-box">No offers found.</div>}

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

function GpuAction({ active }) {
  if (active) {
    return (
      <Link to="/" className="gpu-action active">
        <Sparkles size={20} />
        All Offers
      </Link>
    );
  }
  return (
    <Link to="/gpu" className="gpu-action">
      <Zap size={22} />
      GPU Mode
    </Link>
  );
}

function FilterControls({ filters, options, mode, onChange, onClear }) {
  const regionDetails = (options?.region_details || []).filter((item) => !filters.region || item.region === filters.region);
  const gpuSpecs = options?.gpu_specs || [];

  return (
    <div className="filters">
      <label className="input-wrap wide">
        <span>Search</span>
        <div className="search-input">
          <Search size={16} />
          <input value={filters.search} onChange={(event) => onChange("search", event.target.value)} placeholder="RTX, Tehran, CX..." />
        </div>
      </label>

      <Select label="Provider" value={filters.provider} onChange={(value) => onChange("provider", value)}>
        <option value="">Any</option>
        {(options?.providers || []).map((provider) => (
          <option key={provider.slug} value={provider.slug}>
            {provider.name}
          </option>
        ))}
      </Select>

      <Select label="Region" value={filters.region} onChange={(value) => onChange("region", value)}>
        <option value="">Any</option>
        {(options?.regions || []).map((region) => (
          <option key={region} value={region}>
            {titleCase(region)}
          </option>
        ))}
      </Select>

      <Select label="Region detail" value={filters.region_detail} onChange={(value) => onChange("region_detail", value)}>
        <option value="">Any</option>
        {regionDetails.map((item) => (
          <option key={`${item.region}:${item.region_detail}`} value={item.region_detail}>
            {item.region_detail}
          </option>
        ))}
      </Select>

      <Select label="Billing" value={filters.billing_period} onChange={(value) => onChange("billing_period", value)}>
        <option value="">Any</option>
        {(options?.billing_periods || []).map((period) => (
          <option key={period} value={period}>
            {titleCase(period)}
          </option>
        ))}
      </Select>

      <Select label="Disk" value={filters.disk_type} onChange={(value) => onChange("disk_type", value)}>
        <option value="">Any</option>
        {(options?.disk_types || []).map((disk) => (
          <option key={disk} value={disk}>
            {disk}
          </option>
        ))}
      </Select>

      <div className="number-grid">
        <NumberInput label="Min price IRR" value={filters.min_price_irr} onChange={(value) => onChange("min_price_irr", value)} />
        <NumberInput label="Max price IRR" value={filters.max_price_irr} onChange={(value) => onChange("max_price_irr", value)} />
        <NumberInput label="Min CPU" value={filters.min_cpu_cores} onChange={(value) => onChange("min_cpu_cores", value)} />
        <NumberInput label="Min RAM MB" value={filters.min_ram_mb} onChange={(value) => onChange("min_ram_mb", value)} />
        <NumberInput label="Min disk GB" value={filters.min_disk_gb} onChange={(value) => onChange("min_disk_gb", value)} />
        <NumberInput label="Min VRAM MB" value={filters.min_gpu_memory_mb} onChange={(value) => onChange("min_gpu_memory_mb", value)} disabled={mode !== "gpu" && !filters.gpu_model} />
      </div>

      <Select label="GPU model" value={filters.gpu_model} onChange={(value) => onChange("gpu_model", value)}>
        <option value="">Any</option>
        {gpuSpecs.map((gpu) => (
          <option key={gpu.id} value={gpu.model}>
            {gpu.model}{gpu.memory_mb ? ` ${formatMemory(gpu.memory_mb)}` : ""}
          </option>
        ))}
      </Select>

      <button className="clear-btn" type="button" onClick={onClear}>
        Clear
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

function NumberInput({ label, value, onChange, disabled }) {
  return (
    <label className="input-wrap">
      <span>{label}</span>
      <input disabled={disabled} type="number" min="0" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function OfferRow({ offer, expanded, onToggle, gpuFirst }) {
  const providerUrl = offer.provider?.base_url || offer.source_url;
  const primarySpecs = gpuFirst ? gpuSpecs(offer).concat(vmSpecs(offer).slice(0, 3)) : vmSpecs(offer).concat(gpuSpecs(offer));

  return (
    <article className={`offer-row ${offer.has_gpu ? "gpu-offer" : ""}`}>
      <div className="offer-main">
        <button className="expand-btn" onClick={onToggle} aria-label={expanded ? "Collapse" : "Expand"}>
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
                {offer.provider?.name || "Provider"}
                <ExternalLink size={13} />
              </a>
            ) : (
              <span>{offer.provider?.name}</span>
            )}
            <span>{titleCase(offer.region || "")}</span>
            {offer.region_detail && <span>{offer.region_detail}</span>}
            <span>{titleCase(offer.billing_period)}</span>
          </div>
        </div>
        <div className="price-box">
          <strong>{formatPrice(offer.price_amount_irr)}</strong>
          <span>IRR</span>
        </div>
        <a className="buy-btn" href={offer.buy_url || offer.source_url || providerUrl || "#"} target="_blank" rel="noreferrer">
          Buy
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
          <DetailBlock title="VM specs" items={vmSpecs(offer)} />
          {offer.gpu && <DetailBlock title="GPU specs" items={gpuSpecs(offer)} />}
          <DetailBlock
            title="Market"
            items={[
              { label: "Country", value: offer.country || "-" },
              { label: "City", value: offer.city || "-" },
              { label: "Category", value: offer.category || "-" },
              { label: "Availability", value: offer.available ? "Available" : "Unavailable" },
              { label: "Source ID", value: offer.source_offer_id },
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
      <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1}>
        <ChevronLeft size={17} />
      </button>
      <span>
        {page} / {totalPages}
      </span>
      <button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page >= totalPages}>
        <ChevronRight size={17} />
      </button>
    </div>
  );
}

function vmSpecs(offer) {
  return [
    { icon: Cpu, label: "CPU", value: offer.cpu_cores ? `${formatNumber(offer.cpu_cores)} cores` : "-" },
    { icon: MemoryStick, label: "RAM", value: formatMemory(offer.ram_mb) },
    { icon: HardDrive, label: "Disk", value: `${formatNumber(offer.disk_gb)} GB${offer.disk_type ? ` ${offer.disk_type}` : ""}` },
    { icon: Gauge, label: "Traffic", value: offer.traffic_gb ? `${formatNumber(offer.traffic_gb)} GB` : "-" },
    { icon: MonitorUp, label: "Bandwidth", value: offer.bandwidth_mbps ? `${formatNumber(offer.bandwidth_mbps)} Mbps` : "-" },
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
  if (mode === "gpu") {
    filters.ordering = params.get("ordering") || "price_amount_irr";
  }
  return filters;
}

function buildOfferQuery(filters, page, mode) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  if (mode === "gpu") params.set("has_gpu", "true");
  params.set("page", String(page));
  return params.toString();
}

function formatPrice(value) {
  if (value === null || value === undefined) return "Contact";
  return Number(value).toLocaleString("en-US");
}

function formatMemory(value) {
  if (!value) return "-";
  if (value >= 1024) return `${formatNumber(value / 1024)} GB`;
  return `${formatNumber(value)} MB`;
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  return Number.isInteger(number) ? number.toLocaleString("en-US") : number.toLocaleString("en-US", { maximumFractionDigits: 1 });
}

function titleCase(value) {
  return String(value || "")
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

createRoot(document.getElementById("root")).render(<App />);
