/* static/admin/js/rizz-admin-dashboard.js
   Reads JSON <script> tags emitted via {{ ...|json_script }} and renders
   ApexCharts. Fails silently if a chart container is missing (so admin
   index changes won't break other pages). */
(function () {
    "use strict";

    function readJSON(id, fallback) {
        var el = document.getElementById(id);
        if (!el) return fallback;
        try { return JSON.parse(el.textContent); } catch (e) { return fallback; }
    }

    function ready(fn) {
        if (document.readyState !== "loading") fn();
        else document.addEventListener("DOMContentLoaded", fn);
    }

    ready(function () {
        if (typeof ApexCharts === "undefined") return;

        // ───────── REVENUE AREA CHART ─────────
        var revEl = document.querySelector("#revenue-chart");
        if (revEl) {
            var months = readJSON("chart-months", []);
            var revenue = readJSON("chart-revenue", []);
            new ApexCharts(revEl, {
                chart: { type: "area", height: 300, toolbar: { show: false }, fontFamily: "inherit" },
                series: [{ name: "Revenue ($)", data: revenue }],
                xaxis: { categories: months },
                colors: ["#556ee6"],
                fill: {
                    type: "gradient",
                    gradient: { shadeIntensity: 1, opacityFrom: 0.5, opacityTo: 0.05, stops: [0, 100] },
                },
                dataLabels: { enabled: false },
                stroke: { curve: "smooth", width: 2 },
                grid: { borderColor: "#eef2f7" },
                yaxis: { labels: { formatter: function (v) { return "$" + Math.round(v); } } },
                tooltip: { y: { formatter: function (v) { return "$" + v.toFixed(2); } } },
            }).render();
        }

        // ───────── ORDERS BAR CHART ─────────
        var ordersEl = document.querySelector("#orders-chart");
        if (ordersEl) {
            var months2 = readJSON("chart-months", []);
            var orders = readJSON("chart-orders", []);
            new ApexCharts(ordersEl, {
                chart: { type: "bar", height: 280, toolbar: { show: false }, fontFamily: "inherit" },
                series: [{ name: "Orders", data: orders }],
                xaxis: { categories: months2 },
                colors: ["#34c38f"],
                plotOptions: { bar: { borderRadius: 4, columnWidth: "50%" } },
                dataLabels: { enabled: false },
                grid: { borderColor: "#eef2f7" },
            }).render();
        }

        // ───────── STATUS DONUT ─────────
        var statusEl = document.querySelector("#status-chart");
        if (statusEl) {
            var labels = readJSON("chart-status-labels", []);
            var counts = readJSON("chart-status-counts", []);
            new ApexCharts(statusEl, {
                chart: { type: "donut", height: 300, fontFamily: "inherit" },
                series: counts,
                labels: labels,
                colors: ["#f1b44c", "#34c38f", "#50a5f1", "#556ee6", "#f46a6a"],
                legend: { position: "bottom" },
                dataLabels: { enabled: true },
                plotOptions: { pie: { donut: { size: "65%" } } },
            }).render();
        }
    });
})();