/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";

// ─── Category display helpers ──────────────────────────────────────────────
const CATEGORY_LABELS = {
    it_equipment:    "IT Equipment",
    network_servers: "Network & Servers",
    security_cctv:   "Security & CCTV",
    av_display:      "AV & Display",
    telecom:         "Telecom",
    peripherals:     "Peripherals",
    facilities:      "Facilities",
    tools:           "Tools",
};

const CATEGORY_EMOJIS = {
    it_equipment:    "🖥️",
    network_servers: "🌐",
    security_cctv:   "📷",
    av_display:      "📺",
    telecom:         "📞",
    peripherals:     "🖨️",
    facilities:      "🏢",
    tools:           "🔧",
};

const STATUS_COLORS = {
    in_stock:         "#22c55e",
    assign:           "#6366f1",
    repair:           "#f59e0b",
    service_in_stock: "#0ea5e9",
    expired:          "#ef4444",
    no_stock:         "#e879f9",
    return:           "#94a3b8",
    depreciated:      "#78716c",
    scrap:            "#64748b",
    remote_user:      "#a78bfa",
};

const CHART_COLORS = [
    "#6366f1", "#8b5cf6", "#a855f7", "#ec4899",
    "#0ea5e9", "#22c55e", "#f59e0b", "#ef4444",
];

export class AssetDashboard extends Component {
    static template = "asset_management.AssetDashboard";

    setup() {
        this.orm    = useService("orm");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            activeCategory: "all",
            searchQuery: "",
            data: {
                total_asset_types:   0,
                storable_count:      0,
                service_count:       0,
                total_assets:        0,
                in_stock:            0,
                assigned:            0,
                in_repair:           0,
                transfers:           0,
                by_category:         [],
                status_distribution: [],
                types_per_category:  [],
                company_name:        "",
            },
        });

        this._charts = {};

        // ── Load Chart.js before the component mounts ──────────────────────
        // Odoo 17 does not expose Chart.js as a global; use loadJS to inject
        // it from the CDN so it becomes available as window.Chart.
        onWillStart(async () => {
            await loadJS(
                "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"
            );
        });

        onMounted(async () => {
            await this._loadData();
        });

        onWillUnmount(() => {
            Object.values(this._charts).forEach((c) => c && c.destroy());
        });
    }

    // ── Shorthand for the Chart constructor (now a proper global) ──────────
    get Chart() {
        return window.Chart;
    }

    // ── Data loading ──────────────────────────────────────────────────────
    async _loadData() {
        this.state.loading = true;
        try {
            const result = await this.orm.call(
                "asset.type",
                "get_asset_dashboard_data",
                [this.state.activeCategory === "all" ? false : this.state.activeCategory],
                {}
            );
            this.state.data = result;
        } catch (e) {
            console.error("Dashboard load error:", e);
        }
        this.state.loading = false;
        // Give OWL a tick to re-render the canvas elements before drawing
        setTimeout(() => this._renderCharts(), 60);
    }

    // ── Chart rendering ───────────────────────────────────────────────────
    _renderCharts() {
        this._renderStatusChart();
        this._renderTypesPerCategoryChart();
        this._renderByCategoryChart();
    }

    _renderStatusChart() {
        const canvas = document.getElementById("asset-status-chart");
        if (!canvas || !this.Chart) return;
        if (this._charts.status) this._charts.status.destroy();

        const { status_distribution } = this.state.data;
        if (!status_distribution || status_distribution.length === 0) return;

        const labels = status_distribution.map((s) =>
            s.status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
        );
        const values = status_distribution.map((s) => s.count);
        const colors = status_distribution.map(
            (s) => STATUS_COLORS[s.status] || "#6366f1"
        );

        this._charts.status = new this.Chart(canvas, {
            type: "doughnut",
            data: {
                labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderColor: "#0f172a",
                    borderWidth: 3,
                    hoverOffset: 8,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "62%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#94a3b8",
                            padding: 14,
                            font: { size: 11, weight: "600" },
                            boxWidth: 12,
                            boxHeight: 12,
                        },
                    },
                    tooltip: {
                        backgroundColor: "rgba(15,23,42,0.95)",
                        titleColor: "#f1f5f9",
                        bodyColor: "#94a3b8",
                        borderColor: "rgba(99,102,241,0.3)",
                        borderWidth: 1,
                    },
                },
            },
        });
    }

    _renderTypesPerCategoryChart() {
        const canvas = document.getElementById("types-category-chart");
        if (!canvas || !this.Chart) return;
        if (this._charts.typesCat) this._charts.typesCat.destroy();

        const { types_per_category } = this.state.data;
        if (!types_per_category || types_per_category.length === 0) return;

        const labels = types_per_category.map(
            (t) => CATEGORY_LABELS[t.category] || t.category
        );
        const values = types_per_category.map((t) => t.count);

        this._charts.typesCat = new this.Chart(canvas, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: "Asset Types",
                    data: values,
                    backgroundColor: labels.map((_, i) => CHART_COLORS[i % CHART_COLORS.length] + "CC"),
                    borderColor:     labels.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]),
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false,
                }],
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "rgba(15,23,42,0.95)",
                        titleColor: "#f1f5f9",
                        bodyColor: "#94a3b8",
                        borderColor: "rgba(99,102,241,0.3)",
                        borderWidth: 1,
                    },
                },
                scales: {
                    x: {
                        grid:   { color: "rgba(255,255,255,0.05)" },
                        ticks:  { color: "#64748b", font: { size: 11 } },
                        border: { color: "rgba(255,255,255,0.06)" },
                    },
                    y: {
                        grid:   { display: false },
                        ticks:  { color: "#94a3b8", font: { size: 11, weight: "600" } },
                        border: { color: "rgba(255,255,255,0.06)" },
                    },
                },
            },
        });
    }

    _renderByCategoryChart() {
        const canvas = document.getElementById("by-category-chart");
        if (!canvas || !this.Chart) return;
        if (this._charts.byCategory) this._charts.byCategory.destroy();

        const { by_category } = this.state.data;
        if (!by_category || by_category.length === 0) return;

        const labels = by_category.map((b) => CATEGORY_LABELS[b.category] || b.category);
        const values = by_category.map((b) => b.count);

        this._charts.byCategory = new this.Chart(canvas, {
            type: "polarArea",
            data: {
                labels,
                datasets: [{
                    data: values,
                    backgroundColor: CHART_COLORS.slice(0, labels.length).map((c) => c + "99"),
                    borderColor:     CHART_COLORS.slice(0, labels.length),
                    borderWidth: 2,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#94a3b8",
                            padding: 10,
                            font: { size: 10, weight: "600" },
                            boxWidth: 10,
                            boxHeight: 10,
                        },
                    },
                    tooltip: {
                        backgroundColor: "rgba(15,23,42,0.95)",
                        titleColor: "#f1f5f9",
                        bodyColor: "#94a3b8",
                        borderColor: "rgba(99,102,241,0.3)",
                        borderWidth: 1,
                    },
                },
                scales: {
                    r: {
                        grid:        { color: "rgba(255,255,255,0.06)" },
                        ticks:       { display: false },
                        pointLabels: { display: false },
                    },
                },
            },
        });
    }

    // ── User interactions ─────────────────────────────────────────────────
    async onCategoryClick(category) {
        this.state.activeCategory = category;
        await this._loadData();
    }

    async onSearch(ev) {
        this.state.searchQuery = ev.target.value;
    }

    onExport() {
        this.action.doAction("asset_management.action_assets_settings", {
            additionalContext: { active_test: true },
        });
    }

    onNewAssetType() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "asset.type",
            views: [[false, "form"]],
            target: "current",
        });
    }

    onStatClick(status) {
        if (status === "asset_types") {
            this.action.doAction("asset_management.action_assets_settings");
            return;
        }
        if (status === "transfers") {
            this.action.doAction("asset_management.action_assets_transfer_entry");
            return;
        }
        const domainMap = {
            total_assets: [],
            in_stock:     [["status", "=", "in_stock"]],
            assigned:     [["status", "=", "assign"]],
            in_repair:    [["status", "=", "repair"]],
        };
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Assets",
            res_model: "asset.management",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: domainMap[status] || [],
        });
    }

    // ── Template helpers ──────────────────────────────────────────────────
    get categories() {
        return Object.entries(CATEGORY_LABELS).map(([key, label]) => ({
            key,
            label,
            emoji: CATEGORY_EMOJIS[key] || "📦",
        }));
    }
}

registry
    .category("actions")
    .add("asset_management.asset_dashboard", AssetDashboard);
