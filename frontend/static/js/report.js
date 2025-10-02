function loadReports() {
    let reports = JSON.parse(localStorage.getItem("reports")) || [];
    const reportList = document.getElementById("reportList");
    reportList.innerHTML = "";

    reports.forEach((report, index) => {
        let card = document.createElement("div");
        card.className = "report-card";

        card.innerHTML = `
            <div class="report-header">
                <h3>${report.name}</h3>
                <span class="report-type">${report.type}</span>
            </div>
            <div class="report-meta">
                <p><strong>Date:</strong> ${report.date}</p>
                <p><strong>Authors:</strong> ${report.authors}</p>
                <p><strong>Subject:</strong> ${report.subject}</p>
            </div>

            <div class="toggle-abstract" onclick="toggleAbstract(this)">
                Show abstract <span>▼</span>
            </div>
            <div class="abstract-content">
                <p>${report.description}</p>
            </div>

            <div class="report-actions">
                <button class="action-btn edit-btn" onclick="editReport(${index})">Edit</button>
                <button class="action-btn delete-btn" onclick="deleteReport(${index})">Delete</button>
            </div>
        `;

        reportList.appendChild(card);
    });
}

function toggleAbstract(element) {
    let abstract = element.nextElementSibling;

    if (abstract.classList.contains("show")) {
        abstract.classList.remove("show");
        element.innerHTML = `Show abstract <span>▼</span>`;
    } else {
        abstract.classList.add("show");
        element.innerHTML = `Hide abstract <span>▲</span>`;
    }
}



function deleteReport(index) {
    let reports = JSON.parse(localStorage.getItem("reports")) || [];
    reports.splice(index, 1);
    localStorage.setItem("reports", JSON.stringify(reports));
    loadReports();
}

function editReport(index) {
    let reports = JSON.parse(localStorage.getItem("reports")) || [];
    let report = reports[index];

    let name = prompt("Report Name:", report.name);
    let date = prompt("Date:", report.date);
    let authors = prompt("Authors:", report.authors);
    let type = prompt("Type:", report.type);
    let subject = prompt("Subject:", report.subject);
    let description = prompt("Description:", report.description);

    if (name && date && authors && type && subject && description) {
        reports[index] = { name, date, authors, type, subject, description };
        localStorage.setItem("reports", JSON.stringify(reports));
        loadReports();
    }
}

document.addEventListener("DOMContentLoaded", loadReports);
