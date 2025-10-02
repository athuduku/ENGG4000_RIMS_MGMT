document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("reportForm");

    form.addEventListener("submit", function (event) {
        event.preventDefault();

        const report = {
            name: document.getElementById("report_name").value,
            date: document.getElementById("date").value,
            authors: document.getElementById("authors").value,
            type: document.getElementById("type").value,
            subject: document.getElementById("subject").value,
            description: document.getElementById("description").value
        };

        let reports = JSON.parse(localStorage.getItem("reports")) || [];
        reports.push(report);
        localStorage.setItem("reports", JSON.stringify(reports));

        window.location.href = "/view_reports/"; // Django URL
    });
});
